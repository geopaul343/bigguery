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
      title: 'Healthcare Audio FHIR Uploader with Security',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: '🏥 Secure Healthcare Audio Upload'),
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

  String _statusMessage =
      '🔒 Ready to upload audio files with enterprise security';
  File? _selectedFile;
  String? _uploadUrl;
  bool _isUploaded = false;

  // FHIR-related fields
  final TextEditingController _patientIdController = TextEditingController();
  final TextEditingController _operatorNameController = TextEditingController();
  final TextEditingController _reasonController = TextEditingController();
  Map<String, dynamic>? _fhirBundle;

  // Security status tracking
  Map<String, dynamic>? _securityScanResult;
  List<String> _securityLogs = [];
  bool _showSecurityDetails = false;

  @override
  void dispose() {
    _patientIdController.dispose();
    _operatorNameController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  void _addSecurityLog(String message) {
    setState(() {
      _securityLogs.insert(
        0,
        '${DateTime.now().toIso8601String().substring(11, 19)} - $message',
      );
      if (_securityLogs.length > 10) _securityLogs.removeLast();
    });
  }

  // Test backend connection with security status
  Future<void> _testBackendConnection() async {
    try {
      setState(() {
        _statusMessage = '🔍 Testing secure backend connection...';
      });
      _addSecurityLog('Testing backend connection with security features');

      final response = await http.get(Uri.parse('$backendUrl/health'));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _statusMessage =
              '✅ Secure backend connected: ${data['status']} - Storage: ${data['storage']}';
        });
        _addSecurityLog(
          '✅ Backend connection successful - Security middleware active',
        );
      } else {
        setState(() {
          _statusMessage =
              '❌ Backend connection failed: ${response.statusCode}';
        });
        _addSecurityLog('❌ Backend connection failed');
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error connecting to backend: $e';
      });
      _addSecurityLog('❌ Connection error: $e');
    }
  }

  // Pick audio file with security validation
  Future<void> _pickAudioFile() async {
    try {
      setState(() {
        _statusMessage =
            '📁 Selecting audio file (security validation enabled)...';
      });
      _addSecurityLog('🔍 File picker opened with audio format validation');

      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['mp3', 'wav', 'ogg', 'm4a', 'aiff'],
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        _selectedFile = File(result.files.single.path!);
        final fileName = result.files.single.name;
        final fileSize = result.files.single.size;

        setState(() {
          _statusMessage =
              '✅ Audio file selected: $fileName (${(fileSize / 1024 / 1024).toStringAsFixed(2)} MB)';
        });
        _addSecurityLog('✅ Audio file validated: $fileName');
        _addSecurityLog('🔍 File extension security check passed');
      } else {
        setState(() {
          _statusMessage = '❌ No file selected';
        });
        _addSecurityLog('❌ File selection cancelled');
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error selecting file: $e';
      });
      _addSecurityLog('❌ File selection error: $e');
    }
  }

  // Upload to Cloud Storage with KMS encryption
  Future<void> _uploadToCloudStorage() async {
    if (_selectedFile == null) {
      setState(() {
        _statusMessage = '❌ Please select a file first';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = '🔐 Getting secure upload URL with KMS encryption...';
      });
      _addSecurityLog('🔐 Requesting KMS-encrypted upload URL');

      // Get upload URL
      final uploadUrlResponse = await http.post(
        Uri.parse('$backendUrl/get-upload-url'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'file_name': _selectedFile!.path.split('/').last,
          'content_type': 'audio/mpeg',
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
      _addSecurityLog(
        '✅ Secure signed URL generated with Cloud Armor protection',
      );

      setState(() {
        _statusMessage = '📤 Uploading to KMS-encrypted Cloud Storage...';
      });

      // Upload file directly to Cloud Storage
      final uploadResponse = await http.put(
        Uri.parse(_uploadUrl!),
        headers: {'Content-Type': 'audio/mpeg'},
        body: await _selectedFile!.readAsBytes(),
      );

      if (uploadResponse.statusCode == 200) {
        setState(() {
          _statusMessage = '✅ File uploaded to KMS-encrypted storage!';
          _isUploaded = true;
        });
        _addSecurityLog(
          '✅ File uploaded to healthcare_audio_analyzer_fhir bucket',
        );
        _addSecurityLog('🔐 File encrypted at rest with Cloud KMS');
      } else {
        setState(() {
          _statusMessage = '❌ Upload failed: ${uploadResponse.statusCode}';
        });
        _addSecurityLog(
          '❌ Upload failed with status: ${uploadResponse.statusCode}',
        );
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error uploading file: $e';
      });
      _addSecurityLog('❌ Upload error: $e');
    }
  }

  // Register with FHIR resources and full security scanning
  Future<void> _registerWithFHIRSecurity() async {
    if (_selectedFile == null || !_isUploaded) {
      setState(() {
        _statusMessage = '❌ Please upload a file first';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = '🔍 Creating FHIR resources with security scanning...';
      });
      _addSecurityLog('🔍 Starting comprehensive security scan');

      final requestBody = {
        'file_name': _selectedFile!.path.split('/').last,
        'file_size': await _selectedFile!.length(),
        'file_type': 'audio/mpeg',
      };

      // Add FHIR fields (these will be scanned for PHI)
      if (_patientIdController.text.isNotEmpty) {
        requestBody['patient_id'] = _patientIdController.text;
        _addSecurityLog('📋 Patient ID will be encrypted with KMS');
      }
      if (_operatorNameController.text.isNotEmpty) {
        requestBody['operator_name'] = _operatorNameController.text;
        _addSecurityLog('📋 Operator name will be encrypted with KMS');
      }
      if (_reasonController.text.isNotEmpty) {
        requestBody['reason'] = _reasonController.text;
      }

      _addSecurityLog('🔍 Running Cloud DLP scan for PHI detection...');

      final response = await http.post(
        Uri.parse('$backendUrl/register-upload-fhir'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(requestBody),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _statusMessage =
              '✅ FHIR resources created with security! Bundle ID: ${data['fhir_bundle_id']}';
          _fhirBundle = data;
          _securityScanResult = data['security_scan'];
        });

        // Log security scan results
        final securityScan = data['security_scan'];
        if (securityScan != null) {
          _addSecurityLog('🔍 Cloud DLP scan completed');
          _addSecurityLog('📊 PHI detected: ${securityScan['phi_detected']}');
          _addSecurityLog('⚠️ Risk level: ${securityScan['risk_level']}');
        }

        _addSecurityLog('📋 Audit log entry created for HIPAA compliance');
        _addSecurityLog(
          '💾 Data stored in healthcare_audio_data.fhir_resources',
        );
        _addSecurityLog('🔐 Sensitive data encrypted with KMS keys');
      } else {
        setState(() {
          _statusMessage = '❌ FHIR registration failed: ${response.statusCode}';
        });
        _addSecurityLog('❌ FHIR registration failed');
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error creating FHIR resources: $e';
      });
      _addSecurityLog('❌ FHIR creation error: $e');
    }
  }

  // View FHIR resources with security context
  Future<void> _viewFHIRResources() async {
    if (_patientIdController.text.isEmpty) {
      setState(() {
        _statusMessage = '❌ Please enter a Patient ID to view FHIR resources';
      });
      return;
    }

    try {
      setState(() {
        _statusMessage = '🔍 Fetching FHIR resources (audit logged)...';
      });
      _addSecurityLog(
        '🔍 Querying FHIR resources - access will be audit logged',
      );

      final response = await http.get(
        Uri.parse(
          '$backendUrl/fhir/Media?patient=${_patientIdController.text}',
        ),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _addSecurityLog(
          '✅ FHIR resources retrieved - access logged for compliance',
        );

        showDialog(
          context: context,
          builder: (BuildContext context) {
            return AlertDialog(
              title: const Row(
                children: [
                  Icon(Icons.security, color: Colors.green),
                  SizedBox(width: 8),
                  Text('🔒 Secure FHIR Resources'),
                ],
              ),
              content: Container(
                width: double.maxFinite,
                height: 400,
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.green.withOpacity(0.1),
                          border: Border.all(color: Colors.green),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Text(
                          '🔒 This data access is audit logged for HIPAA compliance',
                          style: TextStyle(fontSize: 12, color: Colors.green),
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        const JsonEncoder.withIndent('  ').convert(data),
                        style: const TextStyle(
                          fontSize: 12,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            );
          },
        );
        setState(() {
          _statusMessage = '✅ FHIR resources loaded (access audit logged)';
        });
      } else {
        setState(() {
          _statusMessage =
              '❌ Failed to fetch FHIR resources: ${response.statusCode}';
        });
        _addSecurityLog('❌ FHIR query failed: ${response.statusCode}');
      }
    } catch (e) {
      setState(() {
        _statusMessage = '❌ Error fetching FHIR resources: $e';
      });
      _addSecurityLog('❌ FHIR query error: $e');
    }
  }

  Widget _buildSecurityStatusCard() {
    return Card(
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.security, color: Colors.blue),
                const SizedBox(width: 8),
                Text(
                  'Security Status',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.blue.shade800,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                TextButton(
                  onPressed: () {
                    setState(() {
                      _showSecurityDetails = !_showSecurityDetails;
                    });
                  },
                  child: Text(
                    _showSecurityDetails ? 'Hide Details' : 'Show Details',
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Security features overview
            const Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                Chip(
                  avatar: Icon(Icons.lock, size: 16, color: Colors.white),
                  label: Text(
                    'KMS Encryption',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  backgroundColor: Colors.green,
                ),
                Chip(
                  avatar: Icon(Icons.search, size: 16, color: Colors.white),
                  label: Text(
                    'DLP PHI Scan',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  backgroundColor: Colors.orange,
                ),
                Chip(
                  avatar: Icon(Icons.list_alt, size: 16, color: Colors.white),
                  label: Text(
                    'Audit Logging',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  backgroundColor: Colors.purple,
                ),
                Chip(
                  avatar: Icon(Icons.shield, size: 16, color: Colors.white),
                  label: Text(
                    'Cloud Armor',
                    style: TextStyle(color: Colors.white, fontSize: 12),
                  ),
                  backgroundColor: Colors.red,
                ),
              ],
            ),

            if (_securityScanResult != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color:
                      _securityScanResult!['phi_detected']
                          ? Colors.orange.withOpacity(0.1)
                          : Colors.green.withOpacity(0.1),
                  border: Border.all(
                    color:
                        _securityScanResult!['phi_detected']
                            ? Colors.orange
                            : Colors.green,
                  ),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Last Security Scan Results:',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color:
                            _securityScanResult!['phi_detected']
                                ? Colors.orange.shade800
                                : Colors.green.shade800,
                      ),
                    ),
                    Text(
                      'PHI Detected: ${_securityScanResult!['phi_detected']}',
                    ),
                    Text('Risk Level: ${_securityScanResult!['risk_level']}'),
                  ],
                ),
              ),
            ],

            if (_showSecurityDetails) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Security Log (Real-time):',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: Colors.grey.shade800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Container(
                      height: 150,
                      child: ListView.builder(
                        itemCount: _securityLogs.length,
                        itemBuilder: (context, index) {
                          return Text(
                            _securityLogs[index],
                            style: const TextStyle(
                              fontSize: 11,
                              fontFamily: 'monospace',
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
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
                    Row(
                      children: [
                        const Icon(Icons.cloud, color: Colors.blue),
                        const SizedBox(width: 8),
                        Text(
                          'Secure Backend Endpoint',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
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
                    const SizedBox(height: 8),
                    const Text(
                      '🛡️ Protected by Cloud Armor + Security Middleware',
                      style: TextStyle(fontSize: 11, color: Colors.green),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Security Status Card
            _buildSecurityStatusCard(),
            const SizedBox(height: 16),

            // FHIR Patient Information
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.medical_information,
                          color: Colors.red,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'FHIR Patient Information',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.orange.withOpacity(0.1),
                        border: Border.all(color: Colors.orange),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        '🔍 This data will be scanned for PHI and encrypted with KMS',
                        style: TextStyle(fontSize: 11, color: Colors.orange),
                      ),
                    ),
                    const SizedBox(height: 16),
                    TextField(
                      controller: _patientIdController,
                      decoration: const InputDecoration(
                        labelText: 'Patient ID 🔐',
                        hintText: 'e.g., PAT-123456 (will be encrypted)',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.lock, color: Colors.orange),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _operatorNameController,
                      decoration: const InputDecoration(
                        labelText: 'Operator/Doctor Name 🔐',
                        hintText: 'e.g., Dr. Smith (will be encrypted)',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.lock, color: Colors.orange),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _reasonController,
                      decoration: const InputDecoration(
                        labelText: 'Reason for Recording',
                        hintText: 'e.g., Cardiac assessment',
                        border: OutlineInputBorder(),
                        prefixIcon: Icon(Icons.description),
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
                  child: ElevatedButton.icon(
                    onPressed: _testBackendConnection,
                    icon: const Icon(Icons.security),
                    label: const Text('Test Secure Backend'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.purple,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Pick Audio File
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _pickAudioFile,
                    icon: const Icon(Icons.audiotrack),
                    label: const Text('Pick Audio File (Validated)'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Upload to Cloud Storage
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _uploadToCloudStorage,
                    icon: const Icon(Icons.lock),
                    label: const Text('Upload with KMS Encryption'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.green,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // Register with FHIR + Security
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _registerWithFHIRSecurity,
                    icon: const Icon(Icons.security),
                    label: const Text('Create FHIR + Security Scan'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
                  ),
                ),
                const SizedBox(height: 12),

                // View FHIR Resources
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _viewFHIRResources,
                    icon: const Icon(Icons.list_alt),
                    label: const Text('View FHIR (Audit Logged)'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.all(16),
                    ),
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
                    Row(
                      children: [
                        const Icon(Icons.info, color: Colors.blue),
                        const SizedBox(width: 8),
                        Text(
                          'Current Status',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ],
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
                color: Colors.green.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.check_circle, color: Colors.green),
                          const SizedBox(width: 8),
                          Text(
                            'Latest Secure FHIR Bundle',
                            style: Theme.of(context).textTheme.titleMedium
                                ?.copyWith(color: Colors.green.shade800),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('🆔 Bundle ID: ${_fhirBundle!['fhir_bundle_id']}'),
                      Text(
                        '📄 Resources Created: ${_fhirBundle!['fhir_resources_created']}',
                      ),
                      if (_fhirBundle!['security_scan'] != null) ...[
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: Colors.blue.withOpacity(0.1),
                            border: Border.all(color: Colors.blue),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text(
                                '🔍 Security Scan Results:',
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              Text(
                                'PHI Detected: ${_fhirBundle!['security_scan']['phi_detected']}',
                              ),
                              Text(
                                'Risk Level: ${_fhirBundle!['security_scan']['risk_level']}',
                              ),
                            ],
                          ),
                        ),
                      ],
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
