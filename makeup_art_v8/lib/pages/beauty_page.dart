import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_client.dart';

class BeautyPage extends StatefulWidget {
  const BeautyPage({super.key, required this.api, required this.onLogout});
  final ApiClient api;
  final VoidCallback onLogout;

  @override
  State<BeautyPage> createState() => _BeautyPageState();
}

class _BeautyPageState extends State<BeautyPage> {
  final picker = ImagePicker();
  XFile? selected;
  Map<String, dynamic>? result;
  double intensity = 0.7;
  bool loading = false;
  String? error;

  Future<void> pick() async {
    final image = await picker.pickImage(source: ImageSource.gallery, imageQuality: 92);
    if (image != null) {
      setState(() { selected = image; result = null; error = null; });
    }
  }

  Future<void> process() async {
    if (selected == null) return;
    setState(() { loading = true; error = null; });
    try {
      final response = await widget.api.processImage(selected!, intensity: intensity);
      if (mounted) setState(() => result = response);
    } catch (_) {
      if (mounted) setState(() => error = 'Could not process this image.');
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final afterUrl = result?['after_image_url'] as String?;
    return Scaffold(
      appBar: AppBar(title: const Text('Beauty Studio'),
        actions: [IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout))]),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text('AI Beauty Preview', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                const Text('Choose a client photo, adjust enhancement strength, then process it securely.'),
                const SizedBox(height: 18),
                if (selected != null)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Image.file(File(selected!.path), height: 300, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const SizedBox(
                        height: 120, child: Center(child: Icon(Icons.image_outlined, size: 56)))),
                  )
                else
                  Container(height: 220,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Theme.of(context).colorScheme.outline)),
                    child: const Center(child: Icon(Icons.face_retouching_natural, size: 64))),
                const SizedBox(height: 14),
                OutlinedButton.icon(onPressed: loading ? null : pick,
                  icon: const Icon(Icons.photo_library_outlined), label: const Text('Choose photo')),
                const SizedBox(height: 12),
                Text('Intensity \${(intensity * 100).round()}%'),
                Slider(value: intensity, onChanged: loading ? null : (v) => setState(() => intensity = v)),
                FilledButton.icon(onPressed: selected == null || loading ? null : process,
                  icon: const Icon(Icons.auto_awesome),
                  label: Text(loading ? 'Processing...' : 'Process with AI')),
                if (error != null) ...[
                  const SizedBox(height: 12),
                  Text(error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ],
              ]),
            ),
          ),
          if (result != null) ...[
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('Result', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 10),
                  Text('Identity similarity: \${result!['identity_similarity']}'),
                  Text('Skin tone: \${result!['skin_tone']}'),
                  Text('Undertone: \${result!['undertone']}'),
                  Text('Foundation: \${result!['foundation_match']}'),
                  if (afterUrl != null) ...[
                    const SizedBox(height: 16),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.network(widget.api.imageUrl(afterUrl), fit: BoxFit.cover),
                    ),
                  ],
                ]),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
