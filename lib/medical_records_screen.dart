import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class MedicalRecordsScreen extends StatefulWidget {
  const MedicalRecordsScreen({super.key});

  @override
  State<MedicalRecordsScreen> createState() => _MedicalRecordsScreenState();
}

class _MedicalRecordsScreenState extends State<MedicalRecordsScreen> {
  final String backendUrl = 'https://data-api-887192895309.us-central1.run.app';
  
  List<Map<String, dynamic>> _medicalRecords = [];
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadMedicalRecords();
  }

  Future<void> _loadMedicalRecords() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await http.get(
        Uri.parse('$backendUrl/get-medical-records'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true) {
          setState(() {
            _medicalRecords = List<Map<String, dynamic>>.from(data['records'] ?? []);
            _isLoading = false;
          });
        } else {
          setState(() {
            _errorMessage = data['message'] ?? 'Failed to load records';
            _isLoading = false;
          });
        }
      } else {
        setState(() {
          _errorMessage = 'Server error: ${response.statusCode}';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Network error: $e';
        _isLoading = false;
      });
    }
  }

  Widget _buildRecordCard(Map<String, dynamic> record) {
    final bool isEncrypted = record['is_encrypted'] ?? false;
    final bool hasError = record['error'] ?? false;
    
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header with encryption status
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  record['file_name'] ?? 'Unknown File',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: hasError 
                        ? Colors.red.shade100
                        : isEncrypted 
                            ? Colors.green.shade100 
                            : Colors.orange.shade100,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    hasError 
                        ? '❌ Error'
                        : isEncrypted 
                            ? '🔐 Decrypted' 
                            : '⚠️ Not Encrypted',
                    style: TextStyle(
                      fontSize: 12,
                      color: hasError 
                          ? Colors.red.shade700
                          : isEncrypted 
                              ? Colors.green.shade700 
                              : Colors.orange.shade700,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // Patient ID
            _buildInfoRow(
              '👤 Patient ID',
              record['patient_id'] ?? 'Unknown',
              hasError ? Colors.red.shade700 : Colors.blue.shade700,
            ),
            
            // Doctor
            _buildInfoRow(
              '👨‍⚕️ Doctor',
              record['doctor'] ?? 'Unknown Doctor',
              hasError ? Colors.red.shade700 : Colors.purple.shade700,
            ),
            
            // Reason for recording
            _buildInfoRow(
              '📝 Reason',
              record['reason'] ?? 'Not specified',
              hasError ? Colors.red.shade700 : Colors.green.shade700,
            ),
            
            // Date
            if (record['date'] != null) ...[
              const SizedBox(height: 8),
              _buildInfoRow(
                '📅 Date',
                _formatDate(record['date']),
                Colors.grey.shade600,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDate(String isoDate) {
    try {
      final date = DateTime.parse(isoDate);
      return '${date.day}/${date.month}/${date.year} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return isoDate;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('🏥 Medical Records'),
        backgroundColor: Colors.blue.shade600,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadMedicalRecords,
            tooltip: 'Refresh Records',
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('🔓 Decrypting medical records...'),
                ],
              ),
            )
          : _errorMessage != null
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.error_outline,
                        size: 64,
                        color: Colors.red,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _errorMessage!,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 16),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: _loadMedicalRecords,
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                )
              : _medicalRecords.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.folder_open,
                            size: 64,
                            color: Colors.grey,
                          ),
                          SizedBox(height: 16),
                          Text(
                            'No medical records found',
                            style: TextStyle(fontSize: 18),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Upload some audio files first',
                            style: TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    )
                  : Column(
                      children: [
                        // Header with count and encryption info
                        Container(
                          width: double.infinity,
                          color: Colors.blue.shade50,
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            children: [
                              Text(
                                '📊 ${_medicalRecords.length} Medical Records',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                '🔐 All sensitive data is encrypted at rest and decrypted for display',
                                style: TextStyle(
                                  color: Colors.green,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                        
                        // Records list
                        Expanded(
                          child: ListView.builder(
                            itemCount: _medicalRecords.length,
                            itemBuilder: (context, index) {
                              return _buildRecordCard(_medicalRecords[index]);
                            },
                          ),
                        ),
                      ],
                    ),
    );
  }
} 