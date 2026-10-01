import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';
import '../services/recent_image_store.dart';

class BeautyPage extends StatefulWidget {
  const BeautyPage({
    super.key,
    required this.api,
    required this.onLogout,
    required this.salonId,
  });

  final ApiClient api;
  final VoidCallback onLogout;
  final String salonId;

  @override
  State<BeautyPage> createState() => _BeautyPageState();
}

class _BeautyPageState extends State<BeautyPage> {
  final picker = ImagePicker();

  RecentImageStore get recentImageStore =>
      RecentImageStore(scope: widget.salonId);

  XFile? selected;
  Map<String, dynamic>? result;
  Future<Uint8List>? afterImageFuture;
  List<Map<String, dynamic>> customers = [];
  String? customerId;
  bool? customerConsentActive;
  double intensity = 0.7;
  bool loading = false;
  bool loadingCustomers = true;
  bool consentConfirmed = false;
  String? error;
  List<File> recentImages = [];

  @override
  void initState() {
    super.initState();
    _loadCustomers();
    _loadRecentImages();
  }

  Future<void> _loadRecentImages() async {
    try {
      final files = await recentImageStore.list();
      if (!mounted) return;
      setState(() => recentImages = files);
    } catch (_) {
      if (mounted) setState(() => recentImages = []);
    }
  }

  Future<void> _showRecentImage(File file) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => Dialog(
        child: InteractiveViewer(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Image.file(file, fit: BoxFit.contain),
          ),
        ),
      ),
    );
  }

  Future<void> _loadCustomers() async {
    if (mounted) setState(() => loadingCustomers = true);
    try {
      final rows = await widget.api.listCustomers();
      if (!mounted) return;
      setState(() => customers = rows);
      if (customerId != null) await _refreshCustomerConsent(customerId!);
    } catch (_) {
      if (mounted) setState(() => error = 'Could not load client profiles.');
    } finally {
      if (mounted) setState(() => loadingCustomers = false);
    }
  }

  Future<void> _selectCustomer(String value) async {
    if (value == 'walk-in') {
      setState(() {
        customerId = null;
        customerConsentActive = null;
      });
      return;
    }
    setState(() {
      customerId = value;
      customerConsentActive = null;
    });
    await _refreshCustomerConsent(value);
  }

  Future<void> _refreshCustomerConsent(String id) async {
    try {
      final consent = await widget.api.getActiveConsent(id);
      if (!mounted || customerId != id) return;
      setState(() => customerConsentActive = consent != null);
    } catch (_) {
      if (mounted) setState(() => customerConsentActive = false);
    }
  }

  Future<void> _toggleStoredConsent() async {
    final id = customerId;
    if (id == null) return;
    final grant = customerConsentActive != true;
    try {
      await widget.api.setCustomerConsent(customerId: id, granted: grant);
      await _refreshCustomerConsent(id);
    } catch (_) {
      if (mounted) setState(() => error = 'Could not update client consent.');
    }
  }

  Future<void> _addCustomer() async {
    final firstName = TextEditingController();
    final lastName = TextEditingController();
    final phone = TextEditingController();

    final payload = await showDialog<Map<String, String>>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Add client'),
        content: SingleChildScrollView(
          child: Column(
            children: [
              TextField(
                controller: firstName,
                decoration: const InputDecoration(labelText: 'First name'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: lastName,
                decoration: const InputDecoration(labelText: 'Last name'),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(labelText: 'Phone (optional)'),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              if (firstName.text.trim().isEmpty || lastName.text.trim().isEmpty) return;
              Navigator.pop(
                dialogContext,
                {
                  'first_name': firstName.text.trim(),
                  'last_name': lastName.text.trim(),
                  'phone': phone.text.trim(),
                },
              );
            },
            child: const Text('Save client'),
          ),
        ],
      ),
    );

    firstName.dispose();
    lastName.dispose();
    phone.dispose();

    if (payload == null) return;

    try {
      final client = await widget.api.createCustomer(
        firstName: payload['first_name']!,
        lastName: payload['last_name']!,
        phone: payload['phone'],
      );
      await _loadCustomers();
      if (!mounted) return;
      setState(() {
        customerId = client['id'] as String;
        customerConsentActive = false;
      });
    } catch (_) {
      if (mounted) setState(() => error = 'Could not create client profile.');
    }
  }

  Future<void> pick(ImageSource source) async {
    final image = await picker.pickImage(source: source, imageQuality: 92);
    if (image == null || !mounted) return;
    setState(() {
      selected = image;
      result = null;
      afterImageFuture = null;
      error = null;
    });
  }

  Future<void> process() async {
    if (selected == null || !consentConfirmed) return;
    if (customerId != null && customerConsentActive != true) return;

    setState(() {
      loading = true;
      error = null;
    });

    try {
      final response = await widget.api.processImage(
        selected!,
        intensity: intensity,
        consentConfirmed: consentConfirmed,
        customerId: customerId,
      );

      Uint8List? afterBytes;
      final afterUrl = response['after_image_url'] as String?;
      if (afterUrl != null) {
        afterBytes = await widget.api.fetchImage(afterUrl);

        try {
          await recentImageStore.save(
            afterBytes,
            jobId: response['job_id']?.toString(),
          );
          await _loadRecentImages();
        } catch (_) {
          // The server result must remain usable even if local caching fails.
        }
      }

      if (!mounted) return;
      setState(() {
        result = response;
        afterImageFuture =
            afterBytes == null ? null : Future<Uint8List>.value(afterBytes);
      });
    } catch (exception) {
      if (!mounted) return;
      final message = exception.toString().toLowerCase();
      setState(() {
        error = message.contains('consent')
            ? 'Client consent is required before processing.'
            : 'Could not process this image. Check the API and image quality.';
      });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  String _customerLabel(String id) {
    for (final item in customers) {
      if (item['id'] == id) {
        return '${item['first_name']} ${item['last_name']}';
      }
    }
    return 'Selected client';
  }

  @override
  Widget build(BuildContext context) {
    final canProcess = selected != null &&
        consentConfirmed &&
        !loading &&
        (customerId == null || customerConsentActive == true);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Beauty Studio'),
        actions: [
          IconButton(
            onPressed: loading ? null : _loadCustomers,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh clients',
          ),
          IconButton(
            onPressed: loading ? null : widget.onLogout,
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Client',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: customerId ?? 'walk-in',
                          decoration: const InputDecoration(
                            labelText: 'Client profile',
                            prefixIcon: Icon(Icons.person_outline),
                          ),
                          items: [
                            const DropdownMenuItem<String>(
                              value: 'walk-in',
                              child: Text('Walk-in / no profile'),
                            ),
                            ...customers.map(
                              (item) => DropdownMenuItem<String>(
                                value: item['id'] as String,
                                child: Text(
                                  '${item['first_name']} ${item['last_name']}',
                                ),
                              ),
                            ),
                          ],
                          onChanged: loading || loadingCustomers
                              ? null
                              : (value) {
                                  if (value != null) _selectCustomer(value);
                                },
                        ),
                      ),
                      const SizedBox(width: 10),
                      IconButton.filledTonal(
                        onPressed: loading ? null : _addCustomer,
                        icon: const Icon(Icons.person_add_alt_1),
                        tooltip: 'Add client',
                      ),
                    ],
                  ),
                  if (customerId != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      'Selected: ${_customerLabel(customerId!)}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 8),
                    Card(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      child: ListTile(
                        leading: Icon(
                          customerConsentActive == true
                              ? Icons.verified_user_outlined
                              : Icons.gpp_bad_outlined,
                        ),
                        title: Text(
                          customerConsentActive == true
                              ? 'AI consent is active'
                              : 'AI consent is not active',
                        ),
                        subtitle: Text(
                          customerConsentActive == true
                              ? 'This client can be processed when operator consent is confirmed.'
                              : 'Grant a stored consent record before processing this client.',
                        ),
                        trailing: TextButton(
                          onPressed: loading ? null : _toggleStoredConsent,
                          child: Text(
                            customerConsentActive == true ? 'Revoke' : 'Grant',
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (recentImages.isNotEmpty) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            'Recent AI results',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        Text(
                          '${recentImages.length}/10',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'The 10 latest AI results are kept on this phone. Older app copies are removed automatically.',
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      height: 112,
                      child: ListView.separated(
                        scrollDirection: Axis.horizontal,
                        itemCount: recentImages.length,
                        separatorBuilder: (_, __) => const SizedBox(width: 10),
                        itemBuilder: (context, index) {
                          final file = recentImages[index];
                          return GestureDetector(
                            onTap: () => _showRecentImage(file),
                            child: ClipRRect(
                              borderRadius: BorderRadius.circular(14),
                              child: SizedBox(
                                width: 96,
                                height: 112,
                                child: Image.file(
                                  file,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => const ColoredBox(
                                    color: Colors.black26,
                                    child: Icon(Icons.broken_image_outlined),
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 14),
          ],
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'AI Beauty Preview',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Choose a client photo, confirm consent, adjust enhancement strength, then process it securely.',
                  ),
                  const SizedBox(height: 18),
                  if (selected != null)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.file(
                        File(selected!.path),
                        height: 300,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const SizedBox(
                          height: 120,
                          child: Center(
                            child: Icon(Icons.image_outlined, size: 56),
                          ),
                        ),
                      ),
                    )
                  else
                    Container(
                      height: 220,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                          color: Theme.of(context).colorScheme.outline,
                        ),
                      ),
                      child: const Center(
                        child: Icon(Icons.face_retouching_natural, size: 64),
                      ),
                    ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed:
                              loading ? null : () => pick(ImageSource.gallery),
                          icon: const Icon(Icons.photo_library_outlined),
                          label: const Text('Gallery'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed:
                              loading ? null : () => pick(ImageSource.camera),
                          icon: const Icon(Icons.camera_alt_outlined),
                          label: const Text('Camera'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text('Intensity ${(intensity * 100).round()}%'),
                  Slider(
                    value: intensity,
                    onChanged: loading
                        ? null
                        : (value) => setState(() => intensity = value),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: consentConfirmed,
                    onChanged: loading
                        ? null
                        : (value) => setState(
                              () => consentConfirmed = value ?? false,
                            ),
                    title: const Text('Client consent confirmed'),
                    subtitle: const Text(
                      'I have permission to process this client image with AI.',
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: canProcess ? process : null,
                    icon: const Icon(Icons.auto_awesome),
                    label: Text(loading ? 'Processing...' : 'Process with AI'),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          if (result != null) ...[
            const SizedBox(height: 18),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Result',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Identity similarity: ${result!['identity_similarity']}',
                    ),
                    Text('Skin tone: ${result!['skin_tone']}'),
                    Text('Undertone: ${result!['undertone']}'),
                    Text('Foundation: ${result!['foundation_match']}'),
                    if (afterImageFuture != null) ...[
                      const SizedBox(height: 16),
                      FutureBuilder<Uint8List>(
                        future: afterImageFuture,
                        builder: (context, snapshot) {
                          if (snapshot.connectionState ==
                              ConnectionState.waiting) {
                            return const SizedBox(
                              height: 220,
                              child: Center(
                                child: CircularProgressIndicator(),
                              ),
                            );
                          }
                          if (snapshot.hasError ||
                              snapshot.data == null ||
                              snapshot.data!.isEmpty) {
                            return const SizedBox(
                              height: 120,
                              child: Center(
                                child: Icon(
                                  Icons.broken_image_outlined,
                                  size: 56,
                                ),
                              ),
                            );
                          }
                          return ClipRRect(
                            borderRadius: BorderRadius.circular(16),
                            child: Image.memory(
                              snapshot.data!,
                              fit: BoxFit.cover,
                            ),
                          );
                        },
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
