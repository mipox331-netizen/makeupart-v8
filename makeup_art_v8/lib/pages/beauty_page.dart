import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';
import '../services/gallery_exporter.dart';
import '../services/photo_look_service.dart';
import '../services/recent_image_store.dart';
import '../widgets/license_page_button.dart';
import '../widgets/developer_branding.dart';
import '../widgets/before_after_comparison.dart';
import 'branding_settings_page.dart';

class BeautyPage extends StatefulWidget {
  const BeautyPage({
    super.key,
    required this.api,
    required this.onLogout,
    required this.salonId,
    this.canManageBranding = false,
  });

  final ApiClient api;
  final VoidCallback onLogout;
  final String salonId;
  final bool canManageBranding;

  @override
  State<BeautyPage> createState() => _BeautyPageState();
}

class _BeautyPageState extends State<BeautyPage> {
  final picker = ImagePicker();

  static const _generativeLooks = <String, String>{
    'natural': 'Natural',
    'soft_glam': 'Soft Glam',
    'full_glam': 'Full Glam',
    'bridal_glam': 'Bridal Glam',
    'smokey_eye': 'Smokey Eye',
    'cat_eye': 'Cat Eye',
    'eyeshadow': 'Eyeshadow',
    'eyeliner': 'Eyeliner',
    'lipstick': 'Lipstick',
    'blush': 'Blush',
    'foundation': 'Foundation',
    'editorial': 'Editorial',
    'sleek_hair': 'Sleek Hair',
    'soft_curls': 'Soft Curls',
    'braided_style': 'Braided Style',
    'elegant_updo': 'Elegant Updo',
  };

  static const _makeupStyles = <String, String>{
    'natural': 'Natural',
    'soft_glam': 'Soft Glam',
    'bridal_rose': 'Bridal Rose',
    'evening_glam': 'Evening Glam',
    'smokey_eye': 'Smokey Eye',
    'cat_eye': 'Cat Eye',
    'eyeshadow': 'Eyeshadow Only',
    'eyeliner': 'Eyeliner Only',
    'lipstick': 'Lipstick Only',
    'blush': 'Blush Only',
  };

  RecentImageStore get recentImageStore =>
      RecentImageStore(scope: widget.salonId);

  XFile? selected;
  Map<String, dynamic>? result;
  Future<Uint8List>? afterImageFuture;
  Uint8List? rawAfterBytes;
  Uint8List? displayedAfterBytes;
  String selectedLook = 'Natural Finish';
  String selectedMakeupStyle = 'natural';
  bool savingGallery = false;
  String selectedEngine = 'classic';
  String selectedGenerativeLook = 'full_glam';
  bool externalAiConsentConfirmed = false;
  bool loadingCapabilities = true;
  Map<String, dynamic> capabilities = {};
  Map<String, dynamic> subscription = {};
  bool loadingSubscription = true;
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
    _loadCapabilities();
    _loadSubscription();
  }

  bool get generativeAvailable =>
      capabilities['generative_available'] == true &&
      !loadingSubscription &&
      subscription['generative_engine_entitled'] == true;

  Future<void> _loadSubscription() async {
    try {
      final current = await widget.api.getSubscription();
      if (!mounted) return;
      setState(() => subscription = current);
    } catch (_) {
      // The server remains authoritative. On older API versions, show options
      // rather than accidentally locking every existing paid customer in the UI.
      if (mounted) setState(() => subscription = {});
    } finally {
      if (mounted) setState(() => loadingSubscription = false);
    }
  }

  List<String> _availableOptions(String key, List<String> fallback) {
    final value = subscription[key];
    if (value is List) return value.whereType<String>().toList();
    return fallback;
  }

  void _showPlanRequired(String plan, String feature) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$feature requires the $plan plan or higher. Contact your platform administrator to upgrade.'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _loadCapabilities() async {
    try {
      final available = await widget.api.getBeautyCapabilities();
      if (!mounted) return;
      setState(() => capabilities = available);
    } catch (_) {
      // Older or unreachable backends fail closed: classic processing remains available.
      if (mounted) setState(() => capabilities = {'classic_available': true});
    } finally {
      if (mounted) setState(() => loadingCapabilities = false);
    }
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
    final nextCustomerId = value == 'walk-in' ? null : value;
    setState(() {
      customerId = nextCustomerId;
      customerConsentActive = null;
      // Consent confirmation applies to the currently selected client and photo only.
      consentConfirmed = false;
      externalAiConsentConfirmed = false;
      selected = null;
      result = null;
      afterImageFuture = null;
      rawAfterBytes = null;
      displayedAfterBytes = null;
      error = null;
    });
    if (nextCustomerId != null) {
      await _refreshCustomerConsent(nextCustomerId);
    }
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
      if (!mounted) return;
      setState(() {
        // A grant/revocation changes the consent state; require a fresh operator confirmation.
        consentConfirmed = false;
        externalAiConsentConfirmed = false;
        result = null;
        afterImageFuture = null;
        error = null;
      });
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
        consentConfirmed = false;
        selected = null;
        result = null;
        afterImageFuture = null;
        rawAfterBytes = null;
        displayedAfterBytes = null;
        error = null;
      });
    } catch (_) {
      if (mounted) setState(() => error = 'Could not create client profile.');
    }
  }

  Future<void> pick(ImageSource source) async {
    try {
      final image = await picker.pickImage(
        source: source,
        imageQuality: 92,
      );
      if (image == null || !mounted) return;
      setState(() {
        selected = image;
        // Every new photo needs fresh consent for both processing and any external provider.
        consentConfirmed = false;
        externalAiConsentConfirmed = false;
        result = null;
        afterImageFuture = null;
        rawAfterBytes = null;
        displayedAfterBytes = null;
        error = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        error = source == ImageSource.camera
            ? 'Camera could not open. Check camera permission and try again.'
            : 'Gallery could not open. Check photo access and try again.';
      });
    }
  }

  Future<void> process() async {
    if (selected == null || !consentConfirmed) return;
    if (selectedEngine == 'generative' &&
        (!generativeAvailable || !externalAiConsentConfirmed)) {
      return;
    }
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
        makeupStyle: selectedMakeupStyle,
        photoFinish: selectedLook,
        engine: selectedEngine,
        generativeLook: selectedGenerativeLook,
        externalAiConsent: externalAiConsentConfirmed,
      );

      Uint8List? afterBytes;
      final afterUrl = response['after_image_url'] as String?;
      if (afterUrl != null) {
        rawAfterBytes = await widget.api.fetchImage(afterUrl);
        // New servers return the applied finish in the persisted result. Older
        // backend versions ignore the query parameter, so retain the local
        // fallback without applying the same grade twice.
        afterBytes = response['photo_finish']?.toString() == selectedLook
            ? Uint8List.fromList(rawAfterBytes!)
            : await PhotoLookService.apply(rawAfterBytes!, selectedLook);

        try {
          await recentImageStore.save(
            afterBytes,
            jobId: response['job_id']?.toString(),
          );
          await _loadRecentImages();
        } catch (_) {
          // Keep the current result usable if local history cannot be updated.
        }
      }

      if (!mounted) return;
      setState(() {
        result = response;
        displayedAfterBytes = afterBytes;
        afterImageFuture =
            afterBytes == null ? null : Future<Uint8List>.value(afterBytes);
      });
    } catch (exception) {
      if (!mounted) return;
      final message = exception.toString().toLowerCase();
      setState(() {
        error = message.contains('external generative ai provider')
            ? 'Confirm that the client agrees to external AI processing.'
            : message.contains('generative makeup is not enabled')
                ? 'Generative AI is not configured on the server. Classic AI is still available.'
                : message.contains('consent')
                    ? 'Client consent is required before processing.'
                    : 'Could not process this image. Check the API and image quality.';
      });
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _selectEngine(String engine) {
    if (engine == 'generative' && !generativeAvailable) return;
    setState(() {
      selectedEngine = engine;
      externalAiConsentConfirmed = false;
      result = null;
      afterImageFuture = null;
      rawAfterBytes = null;
      displayedAfterBytes = null;
      error = null;
    });
  }

  void _selectLook(String look) {
    // The current result is already processed and watermarked on the server.
    // Choosing another finish invalidates it and requires a new processing run;
    // re-grading the output locally would apply the finish twice and make the
    // preview/export differ from the persisted result in Google Drive.
    setState(() {
      selectedLook = look;
      result = null;
      afterImageFuture = null;
      rawAfterBytes = null;
      displayedAfterBytes = null;
      error = null;
    });
  }

  Future<void> _saveResultToGallery() async {
    final bytes = displayedAfterBytes;
    if (bytes == null || bytes.isEmpty || savingGallery) return;

    setState(() {
      savingGallery = true;
      error = null;
    });
    try {
      final fileName = 'makeupart_${DateTime.now().millisecondsSinceEpoch}.png';
      await GalleryExporter.savePng(bytes: bytes, fileName: fileName);
      try {
        await recentImageStore.save(
          bytes,
          jobId: result?['job_id']?.toString(),
        );
        await _loadRecentImages();
      } catch (_) {
        // Saving to the public gallery succeeds independently of app history.
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Image saved to your phone Gallery / Photos.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not save image. Check photo permissions and try again.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() => savingGallery = false);
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
    final availableMakeupStyles = _availableOptions(
      'available_makeup_styles',
      _makeupStyles.keys.toList(),
    );
    final availablePhotoFinishes = _availableOptions(
      'available_photo_finishes',
      PhotoLookService.names,
    );
    final canProcess = selected != null &&
        consentConfirmed &&
        (selectedEngine != 'generative' ||
            (generativeAvailable && externalAiConsentConfirmed)) &&
        !loadingSubscription &&
        !loading &&
        (customerId == null || customerConsentActive == true);

    return Scaffold(
      appBar: AppBar(
        title: const Text('MakeupArt Studio'),
        actions: [
          if (widget.canManageBranding)
            IconButton(
              tooltip: 'Salon branding and watermark',
              onPressed: loading
                  ? null
                  : () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => BrandingSettingsPage(api: widget.api),
                        ),
                      ),
              icon: const Icon(Icons.tune_rounded),
            ),
          const LicensePageButton(),
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
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF44255C), Color(0xFF191B2D), Color(0xFF10131C)],
              ),
              borderRadius: BorderRadius.circular(26),
              border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: const Icon(Icons.auto_awesome_rounded, size: 28),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('BEAUTY WORKSPACE',
                              style: TextStyle(fontSize: 11, letterSpacing: 1.6)),
                          SizedBox(height: 4),
                          Text('Create a salon-ready result',
                              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Choose a portrait, apply skin polish and a face-guided lip / cheek treatment, select a photo finish, then save a branded image.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.white.withValues(alpha: .78),
                      ),
                ),
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerRight,
                  child: DeveloperBranding(compact: true),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
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
                          key: ValueKey(customerId ?? 'walk-in'),
                          initialValue: customerId ?? 'walk-in',
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
                      'The 10 latest results stay in the app. On Android, older results are archived to a salon-specific app folder when phone storage is available. They are not added to the public Gallery, and Android may remove that app folder when MakeupArt is uninstalled. If archiving is unavailable, older results are kept rather than deleted.',
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
                  const SizedBox(height: 18),
                  Text(
                    'AI engine',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ChoiceChip(
                        avatar: const Icon(Icons.tune_rounded, size: 18),
                        label: const Text('Classic AI'),
                        selected: selectedEngine == 'classic',
                        onSelected: loading ? null : (_) => _selectEngine('classic'),
                      ),
                      ChoiceChip(
                        avatar: const Icon(Icons.auto_awesome_rounded, size: 18),
                        label: const Text('Generative AI'),
                        selected: selectedEngine == 'generative',
                        onSelected: loading || !generativeAvailable
                            ? null
                            : (_) => _selectEngine('generative'),
                      ),
                    ],
                  ),
                  if (loadingCapabilities) ...[
                    const SizedBox(height: 8),
                    const LinearProgressIndicator(),
                  ],
                  if (!loadingCapabilities && !generativeAvailable) ...[
                    const SizedBox(height: 8),
                    const ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading: Icon(Icons.info_outline_rounded),
                      title: Text('Generative makeup is not enabled yet'),
                      subtitle: Text(
                        'The server needs the protected OPENAI_API_KEY secret and a production redeploy. Classic AI remains available. Generative processing may have provider charges.',
                      ),
                    ),
                  ],
                  if (selectedEngine == 'generative') ...[
                    const SizedBox(height: 14),
                    Text(
                      'Generative look',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _generativeLooks.entries.map((look) {
                        return ChoiceChip(
                          avatar: const Icon(Icons.auto_awesome_rounded, size: 17),
                          label: Text(look.value),
                          selected: selectedGenerativeLook == look.key,
                          onSelected: loading
                              ? null
                              : (_) => setState(() {
                                    selectedGenerativeLook = look.key;
                                    result = null;
                                    afterImageFuture = null;
                                    rawAfterBytes = null;
                                    displayedAfterBytes = null;
                                    externalAiConsentConfirmed = false;
                                    error = null;
                                  }),
                        );
                      }).toList(),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Generative edits send the photo to an external image provider and may incur usage charges. Generated images can change facial details; review every result.',
                    ),
                    CheckboxListTile(
                      contentPadding: EdgeInsets.zero,
                      value: externalAiConsentConfirmed,
                      onChanged: loading
                          ? null
                          : (value) => setState(
                                () => externalAiConsentConfirmed = value ?? false,
                              ),
                      title: const Text('Client agrees to external AI processing'),
                      subtitle: const Text(
                        'I have permission to send this photo to the configured third-party image provider for this edit.',
                      ),
                    ),
                  ] else ...[
                    Text(
                      'Makeup style',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 5),
                    const Text(
                      'Use complete looks or a single local effect. Smokey Eye, Cat Eye, Eyeshadow Only, Eyeliner Only, Lipstick Only and Blush Only work without a paid AI key.',
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: _makeupStyles.entries.map((style) {
                        final entitled = availableMakeupStyles.contains(style.key);
                        final requiredPlan = style.key == 'soft_glam' ? 'Basic' : 'Pro';
                        return ChoiceChip(
                          avatar: Icon(
                            entitled
                                ? Icons.face_retouching_natural_rounded
                                : Icons.lock_outline_rounded,
                            size: 17,
                          ),
                          label: Text(style.value),
                          selected: selectedMakeupStyle == style.key,
                          onSelected: loading
                              ? null
                              : (_) {
                                  if (!entitled) {
                                    _showPlanRequired(requiredPlan, style.value);
                                    return;
                                  }
                                  setState(() {
                                    selectedMakeupStyle = style.key;
                                    result = null;
                                    afterImageFuture = null;
                                    rawAfterBytes = null;
                                    displayedAfterBytes = null;
                                    error = null;
                                  });
                                },
                        );
                      }).toList(),
                    ),
                  ],
                  const SizedBox(height: 18),
                  Text(
                    'Photo finish',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'Photo finishes adjust the overall color tone. For eye, lip and cheek makeup, choose a style above. Hair color and hairstyle generation are not available in the free Classic engine.',
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: PhotoLookService.names.map((look) {
                      final entitled = availablePhotoFinishes.contains(look);
                      final requiredPlan = look == 'Soft Glam' ? 'Basic' : 'Pro';
                      return ChoiceChip(
                        avatar: Icon(
                          !entitled
                              ? Icons.lock_outline_rounded
                              : selectedLook == look
                                  ? Icons.check_circle_rounded
                                  : Icons.auto_awesome_outlined,
                          size: 17,
                        ),
                        label: Text(look),
                        selected: selectedLook == look,
                        onSelected: loading
                            ? null
                            : (_) {
                                if (!entitled) {
                                  _showPlanRequired(requiredPlan, look);
                                  return;
                                }
                                _selectLook(look);
                              },
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 16),
                  Text('${selectedEngine == 'generative' ? 'Treatment strength' : 'Skin polish strength'} ${(intensity * 100).round()}%'),
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
                      selectedEngine == 'generative'
                          ? 'Generative look: ${_generativeLooks[result!['generative_look']] ?? result!['generative_look'] ?? selectedGenerativeLook}'
                          : 'Makeup style: ${_makeupStyles[selectedMakeupStyle] ?? selectedMakeupStyle}',
                    ),
                    if (result!['engine'] == 'generative')
                      const Text(
                        'AI-generated edit: review facial details before using it as a client reference.',
                      )
                    else if (result!['identity_similarity'] != null)
                      Text(
                        'Image structure preservation score: ${result!['identity_similarity']}',
                      ),
                    Text('Skin tone: ${result!['skin_tone']}'),
                    Text('Undertone: ${result!['undertone']}'),
                    Text('Foundation match estimate: ${result!['foundation_match']}'),
                    const SizedBox(height: 14),
                    if (afterImageFuture != null && selected != null) ...[
                      const SizedBox(height: 16),
                      const Text(
                        'Drag the divider to compare the original photo with the finished result.',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 10),
                      FutureBuilder<Uint8List>(
                        future: afterImageFuture,
                        builder: (context, snapshot) {
                          if (snapshot.connectionState == ConnectionState.waiting) {
                            return const SizedBox(
                              height: 220,
                              child: Center(child: CircularProgressIndicator()),
                            );
                          }
                          if (snapshot.hasError ||
                              snapshot.data == null ||
                              snapshot.data!.isEmpty) {
                            return const SizedBox(
                              height: 120,
                              child: Center(
                                child: Icon(Icons.broken_image_outlined, size: 56),
                              ),
                            );
                          }
                          return BeforeAfterComparison(
                            key: ValueKey(
                              result?['job_id']?.toString() ?? selected!.path,
                            ),
                            height: 360,
                            before: Image.file(
                              File(selected!.path),
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Icon(
                                Icons.broken_image_outlined,
                                size: 48,
                              ),
                            ),
                            after: Image.memory(
                              snapshot.data!,
                              fit: BoxFit.contain,
                              errorBuilder: (_, __, ___) => const Icon(
                                Icons.broken_image_outlined,
                                size: 48,
                              ),
                            ),
                          );
                        },
                      ),
                    ],
                    if (displayedAfterBytes != null) ...[
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: savingGallery || loading ? null : _saveResultToGallery,
                        icon: savingGallery
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.download_rounded),
                        label: Text(
                          savingGallery ? 'Saving image...' : 'Save result to Gallery',
                        ),
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 15),
                        ),
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'The saved PNG includes the selected photo finish and the salon watermark from the latest processing run.',
                        textAlign: TextAlign.center,
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
