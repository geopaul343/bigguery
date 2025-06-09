import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:googleapis/storage/v1.dart' as storage;
import 'package:googleapis/bigquery/v2.dart' as bigquery;
import 'package:googleapis_auth/auth_io.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/services.dart';
import 'dart:io';
import 'dart:convert';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MyHomePage(title: 'Flutter Demo Home Page'),
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
  bool _isUploading = false;
  bool _isPicking = false;
  bool _isLoadingToBigQuery = false;
  String? _uploadStatus;
  File? _selectedFile;
  String? _uploadedFileName;

  Future<void> _pickFile() async {
    try {
      setState(() {
        _isPicking = true;
        _uploadStatus = 'Picking file...';
      });

      // Pick audio file using file_picker
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.audio,
        allowMultiple: false,
      );

      if (result == null) {
        setState(() {
          _uploadStatus = 'No file selected';
        });
        return;
      }

      setState(() {
        _selectedFile = File(result.files.single.path!);
        _uploadStatus = 'File selected: ${result.files.single.name}';
      });
    } catch (e) {
      setState(() {
        _uploadStatus = 'Error picking file: $e';
      });
    } finally {
      setState(() {
        _isPicking = false;
      });
    }
  }

  Future<void> _uploadFile() async {
    if (_selectedFile == null) {
      setState(() {
        _uploadStatus = 'Please select a file first';
      });
      return;
    }

    try {
      setState(() {
        _isUploading = true;
        _uploadStatus = 'Uploading file...';
      });

      final fileName = _selectedFile!.path.split('/').last;
      final fileExtension = fileName.split('.').last.toLowerCase();

      // Initialize Google Cloud Storage - Load credentials from assets
      final String credentialsJson = await rootBundle.loadString(
        'assets/service-account-key.json',
      );
      final credentials = ServiceAccountCredentials.fromJson(
        jsonDecode(credentialsJson),
      );

      final client = await clientViaServiceAccount(credentials, [
        storage.StorageApi.devstorageFullControlScope,
        bigquery.BigqueryApi.bigqueryScope,
      ]);

      final storageApi = storage.StorageApi(client);

      // Set content type for audio files
      String contentType = 'audio/$fileExtension';
      if (!['mp3', 'wav', 'ogg', 'm4a'].contains(fileExtension)) {
        setState(() {
          _uploadStatus = 'Only audio files (mp3, wav, ogg, m4a) are supported';
          _isUploading = false;
        });
        return;
      }

      final media = storage.Media(
        _selectedFile!.openRead(),
        await _selectedFile!.length(),
        contentType: contentType,
      );

      await storageApi.objects.insert(
        storage.Object(),
        'healthcare_audio_analyzer_fhir',
        uploadMedia: media,
        name: fileName,
      );

      setState(() {
        _uploadStatus = 'File uploaded successfully!';
        _uploadedFileName = fileName;
        _selectedFile = null;
      });
    } catch (e) {
      setState(() {
        _uploadStatus = 'Error uploading file: $e';
      });
    } finally {
      setState(() {
        _isUploading = false;
      });
    }
  }

  Future<void> _loadToBigQuery() async {
    if (_uploadedFileName == null) {
      setState(() {
        _uploadStatus = 'Please upload a file first';
      });
      return;
    }

    try {
      setState(() {
        _isLoadingToBigQuery = true;
        _uploadStatus = 'Loading file to BigQuery...';
      });

      // Initialize BigQuery API
      final String credentialsJson = await rootBundle.loadString(
        'assets/service-account-key.json',
      );
      final credentialsMap = jsonDecode(credentialsJson);
      final credentials = ServiceAccountCredentials.fromJson(credentialsMap);

      final client = await clientViaServiceAccount(credentials, [
        bigquery.BigqueryApi.bigqueryScope,
      ]);

      final bigQueryApi = bigquery.BigqueryApi(client);

      // Get project ID from credentials
      final projectId = credentialsMap['project_id'] as String;

      // Create dataset if it doesn't exist
      const datasetId = 'healthcare_audio_data';
      try {
        await bigQueryApi.datasets.get(projectId, datasetId);
      } catch (e) {
        // Dataset doesn't exist, create it
        final dataset =
            bigquery.Dataset()
              ..datasetReference =
                  (bigquery.DatasetReference()
                    ..projectId = projectId
                    ..datasetId = datasetId)
              ..friendlyName = 'Healthcare Audio Data'
              ..description = 'Dataset for healthcare audio files';

        await bigQueryApi.datasets.insert(dataset, projectId);
      }

      // Create table if it doesn't exist
      const tableId = 'audio_files';
      try {
        await bigQueryApi.tables.get(projectId, datasetId, tableId);
      } catch (e) {
        // Table doesn't exist, create it
        final table =
            bigquery.Table()
              ..tableReference =
                  (bigquery.TableReference()
                    ..projectId = projectId
                    ..datasetId = datasetId
                    ..tableId = tableId)
              ..friendlyName = 'Audio Files'
              ..description = 'Table containing audio file metadata'
              ..schema =
                  (bigquery.TableSchema()
                    ..fields = [
                      bigquery.TableFieldSchema()
                        ..name = 'file_name'
                        ..type = 'STRING'
                        ..mode = 'REQUIRED'
                        ..description = 'Name of the audio file',
                      bigquery.TableFieldSchema()
                        ..name = 'file_path'
                        ..type = 'STRING'
                        ..mode = 'REQUIRED'
                        ..description = 'Cloud Storage path of the file',
                      bigquery.TableFieldSchema()
                        ..name = 'upload_timestamp'
                        ..type = 'TIMESTAMP'
                        ..mode = 'REQUIRED'
                        ..description = 'When the file was uploaded',
                      bigquery.TableFieldSchema()
                        ..name = 'file_size_bytes'
                        ..type = 'INTEGER'
                        ..mode = 'NULLABLE'
                        ..description = 'Size of the file in bytes',
                    ]);

        await bigQueryApi.tables.insert(table, projectId, datasetId);
      }

      // Insert file metadata into BigQuery table
      final row =
          bigquery.TableDataInsertAllRequestRows()
            ..json = {
              'file_name': _uploadedFileName,
              'file_path':
                  'gs://healthcare_audio_analyzer_fhir/$_uploadedFileName',
              'upload_timestamp': DateTime.now().toUtc().toIso8601String(),
              'file_size_bytes': await _selectedFile?.length(),
            };

      final insertRequest = bigquery.TableDataInsertAllRequest()..rows = [row];

      await bigQueryApi.tabledata.insertAll(
        insertRequest,
        projectId,
        datasetId,
        tableId,
      );

      setState(() {
        _uploadStatus =
            'File metadata loaded to BigQuery successfully!\nDataset: $datasetId\nTable: $tableId';
        _uploadedFileName = null;
      });
    } catch (e) {
      setState(() {
        _uploadStatus = 'Error loading to BigQuery: $e';
      });
    } finally {
      setState(() {
        _isLoadingToBigQuery = false;
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
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // First Button - Pick Audio File
              ElevatedButton.icon(
                onPressed: _isPicking ? null : _pickFile,
                icon: const Icon(Icons.folder_open),
                label: Text(_isPicking ? "Picking..." : "Pick Audio File"),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
              ),

              const SizedBox(height: 20),

              // Second Button - Upload to Cloud Storage
              ElevatedButton.icon(
                onPressed:
                    (_isUploading || _selectedFile == null)
                        ? null
                        : _uploadFile,
                icon: const Icon(Icons.cloud_upload),
                label: Text(
                  _isUploading ? "Uploading..." : "Upload to Cloud Storage",
                ),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  backgroundColor: Colors.green,
                  foregroundColor: Colors.white,
                ),
              ),

              const SizedBox(height: 20),

              // Third Button - Load to BigQuery
              ElevatedButton.icon(
                onPressed:
                    (_isLoadingToBigQuery || _uploadedFileName == null)
                        ? null
                        : _loadToBigQuery,
                icon: const Icon(Icons.analytics),
                label: Text(
                  _isLoadingToBigQuery
                      ? "Loading to BigQuery..."
                      : "Load to BigQuery",
                ),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 15),
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
              ),

              const SizedBox(height: 30),

              // Status Message
              if (_uploadStatus != null)
                Container(
                  padding: const EdgeInsets.all(16.0),
                  decoration: BoxDecoration(
                    color: Colors.grey[100],
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.grey[300]!),
                  ),
                  child: Text(
                    _uploadStatus!,
                    style: const TextStyle(fontSize: 16),
                    textAlign: TextAlign.center,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
