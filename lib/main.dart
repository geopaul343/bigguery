import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Healthcare Audio FHIR Uploader',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: 'Healthcare Audio FHIR Upload'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  final String backendUrl = 'https://data-api-887192895309.us-central1.run.app';

  String _statusMessage = 'Ready to upload audio files with FHIR support';
  File? _selectedFile;
  String? _uploadUrl;
  bool _isUploaded = false;

  // FHIR-related fields
  final TextEditingController _patientIdController = TextEditingController();
  final TextEditingController _operatorNameController = TextEditingController();
  final TextEditingController _reasonController = TextEditingController();
  Map<String, dynamic>? _fhirBundle;

  @override
  void dispose() {
    _patientIdController.dispose();
    _operatorNameController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  // Test backend connection
  Future<void> _testBackendConnection() async {
    try {
      setState(() {
        _statusMessage = 'Testing backend connection...';
      });

      final response = await http.get(Uri.parse('$backendUrl/health'));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _statusMessage =
              '✅ Backend connected: ${data['status']} - Storage: ${data['storage']}';
        });
      } else {
        setState(() {
          _statusMessage =
              '❌ Backend connection failed: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error connecting to backend: $e';
      });
    }
  }

  // Pick audio file
  Future<void> _pickAudioFile() async {
    try {
      setState(() {
        _statusMessage = 'Selecting audio file...';
      });

      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['mp3', 'wav', 'ogg', 'm4a'],
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        _selectedFile = File(result.files.single.path!);
        setState(() {
          _statusMessage =
              '📁 File selected: ${result.files.single.name} (${result.files.single.size} bytes)';
        });
      } else {
        setState(() {
          _statusMessage = '❌ No file selected';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error selecting file: $e';
      });
    }
  }

  // Upload to Cloud Storage
  Future<void> _uploadToCloudStorage() async {
    if (_selectedFile == null) {
      setState(() {
        _statusMessage = '❌ Please select a file first';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = 'Getting upload URL...';
      });

      // Get upload URL
      final uploadUrlResponse = await http.post(
        Uri.parse('$backendUrl/get-upload-url'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'file_name': _selectedFile!.path.split('/').last,
          'content_type': 'audio/mpeg', // Adjust based on file type
        }),
      );

      if (uploadUrlResponse.statusCode != 200) {
        setState(() {
          _statusMessage =
              '❌ Failed to get upload URL: ${uploadUrlResponse.statusCode}';
        });
        return;
      }

      final uploadData = jsonDecode(uploadUrlResponse.body);
      _uploadUrl = uploadData['upload_url'];

      setState(() {
        _statusMessage = 'Uploading file to Cloud Storage...';
      });

      // Upload file directly to Cloud Storage
      final uploadResponse = await http.put(
        Uri.parse(_uploadUrl!),
        headers: {'Content-Type': 'audio/mpeg'},
        body: await _selectedFile!.readAsBytes(),
      );

      if (uploadResponse.statusCode == 200) {
        setState(() {
          _statusMessage = '✅ File uploaded successfully to Cloud Storage!';
          _isUploaded = true;
        });
      } else {
        setState(() {
          _statusMessage = '❌ Upload failed: ${uploadResponse.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error uploading file: $e';
      });
    }
  }

  // Register in BigQuery (Traditional)
  Future<void> _registerInBigQuery() async {
    if (_selectedFile == null || !_isUploaded) {
      setState(() {
        _statusMessage = '❌ Please upload a file first';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = 'Registering in BigQuery...';
      });

      final response = await http.post(
        Uri.parse('$backendUrl/register-upload'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'file_name': _selectedFile!.path.split('/').last,
          'file_size': await _selectedFile!.length(),
          'file_type': 'audio/mpeg',
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _statusMessage = '✅ Registered in BigQuery successfully!';
        });
      } else {
        setState(() {
          _statusMessage =
              '❌ BigQuery registration failed: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error registering in BigQuery: $e';
      });
    }
  }

  // Register with FHIR resources
  Future<void> _registerWithFHIR() async {
    if (_selectedFile == null || !_isUploaded) {
      setState(() {
        _statusMessage = '❌ Please upload a file first';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = 'Creating FHIR resources...';
      });

      final requestBody = {
        'file_name': _selectedFile!.path.split('/').last,
        'file_size': await _selectedFile!.length(),
        'file_type': 'audio/mpeg',
      };

      // Add optional FHIR fields if provided
      if (_patientIdController.text.isNotEmpty) {
        requestBody['patient_id'] = _patientIdController.text;
      }
      if (_operatorNameController.text.isNotEmpty) {
        requestBody['operator_name'] = _operatorNameController.text;
      }
      if (_reasonController.text.isNotEmpty) {
        requestBody['reason'] = _reasonController.text;
      }

      final response = await http.post(
        Uri.parse('$backendUrl/register-upload-fhir'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _statusMessage =
              '✅ FHIR resources created! Bundle ID: ${data['fhir_bundle_id']}';
          _fhirBundle = data;
        });
      } else {
        setState(() {
          _statusMessage = '❌ FHIR registration failed: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error creating FHIR resources: $e';
      });
    }
  }

  // View FHIR resources
  Future<void> _viewFHIRResources() async {
    if (_patientIdController.text.isEmpty) {
      setState(() {
        _statusMessage = '❌ Please enter a Patient ID to view FHIR resources';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = 'Fetching FHIR resources...';
      });

      final response = await http.get(
        Uri.parse(
          '$backendUrl/fhir/Media?patient=${_patientIdController.text}',
        ),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        showDialog(
          context: context,
          builder: (BuildContext context) {
            return AlertDialog(
              title: Text('FHIR Media Resources'),
              content: Container(
                width: double.maxFinite,
                height: 400,
                child: SingleChildScrollView(
                  child: Text(
                    const JsonEncoder.withIndent('  ').convert(data),
                    style: TextStyle(fontSize: 12, fontFamily: 'monospace'),
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: Text('Close'),
                ),
              ],
            );
          },
        );
        setState(() {
          _statusMessage = '✅ FHIR resources loaded successfully';
        });
      } else {
        setState(() {
          _statusMessage =
              '❌ Failed to fetch FHIR resources: ${response.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error fetching FHIR resources: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: <Widget>[
            // Backend URL Display
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Text(
                      'Backend URL',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      backendUrl,
                      style: const TextStyle(
                        fontSize: 12,
                        fontFamily: 'monospace',
                        color: Colors.blue,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // FHIR Patient Information
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'FHIR Patient Information (Optional)',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _patientIdController,
                      decoration: const InputDecoration(
                        labelText: 'Patient ID',
                        hintText: 'e.g., 12345',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _operatorNameController,
                      decoration: const InputDecoration(
                        labelText: 'Operator/Doctor Name',
                        hintText: 'e.g., Dr. Smith',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _reasonController,
                      decoration: const InputDecoration(
                        labelText: 'Reason for Recording',
                        hintText: 'e.g., Cardiac assessment',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Action Buttons
            Column(
              children: [
                // Test Backend Connection
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _testBackendConnection,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purple,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('💜 Test Backend Connection'),
                  ),
                ),
                const SizedBox(height: 12),

                // Pick Audio File
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _pickAudioFile,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('🔵 Pick Audio File'),
                  ),
                ),
                const SizedBox(height: 12),

                // Upload to Cloud Storage
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _uploadToCloudStorage,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('🟢 Upload to Cloud Storage'),
                  ),
                ),
                const SizedBox(height: 12),

                // Register in BigQuery (Traditional)
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _registerInBigQuery,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.orange,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('🟠 Register in BigQuery'),
                  ),
                ),
                const SizedBox(height: 12),

                // Register with FHIR
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _registerWithFHIR,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('🔴 Create FHIR Resources'),
                  ),
                ),
                const SizedBox(height: 12),

                // View FHIR Resources
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _viewFHIRResources,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                    child: const Text('🔍 View FHIR Resources'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // Status Message
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Text(
                      'Status',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _statusMessage,
                      style: const TextStyle(fontSize: 14),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            ),

            // FHIR Bundle Information (if available)
            if (_fhirBundle != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Latest FHIR Bundle',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text('Bundle ID: ${_fhirBundle!['fhir_bundle_id']}'),
                      Text(
                        'Resources Created: ${_fhirBundle!['fhir_resources_created']}',
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
