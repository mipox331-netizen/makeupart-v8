import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';
import '../services/favorite_image_store.dart';
import '../services/gallery_exporter.dart';
import '../services/photo_look_service.dart';
import '../services/recent_image_store.dart';
import '../services/share_image_service.dart';
import '../widgets/license_page_button.dart';
import 'favorites_page.dart';
import 'settings_page.dart';

class BeautyPage extends StatefulWidget {
  const BeautyPage({
    super.key,
    required this.api,
    required this.onLogout,
    required this.salonId,
    this.canManageBranding = false,
    this.subscription = const {},
  });

  final ApiClient api;
  final VoidCallback onLogout;
  final String salonId;
  final bool canManageBranding;
  final Map<String, dynamic> subscription;

  @override
  State<BeautyPage> createState() => _BeautyPageState();
}

class _BeautyPageState extends State<BeautyPage> {
  final picker = ImagePicker();

  static const _makeupStyles = <String, String>{
    'natural': 'Natural',
    'soft_glam': 'Soft Glam',
    'bridal_rose': 'Bridal Rose',
    'evening_glam': 'Evening Glam',
  };

  RecentImageStore get recentImageStore =>
      RecentImageStore(scope: widget.salonId);

  FavoriteImageStore get favoriteImageStore =>
      FavoriteImageStore(scope: widget.salonId);

  XFile? selected;
  Map<String, dynamic>? result;
  Future<Uint8List>? afterImageFuture;
  Uint8List? rawAfterBytes;
  Uint8List? displayedAfterBytes;
  String selectedLook = 'Natural Finish';
  String selectedMakeupStyle = 'natural';
  bool showOriginal = false;
  bool savingGallery = false;
  bool savingFavorite = false;
  bool sharingResult = false;
  bool isFavorite = false;
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
    final nextCustomerId = value == 'walk-in' ? null : value;
    setState(() {
      customerId = nextCustomerId;
      customerConsentActive = null;
      // Consent confirmation applies to the currently selected client and photo only.
      consentConfirmed = false;
      selected = null;
      result = null;
      afterImageFuture = null;
      rawAfterBytes = null;
      displayedAfterBytes = null;
      showOriginal = false;
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
        showOriginal = false;
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
        // Every new photo needs its own explicit consent confirmation.
        consentConfirmed = false;
        result = null;
        afterImageFuture = null;
        rawAfterBytes = null;
        displayedAfterBytes = null;
        showOriginal = false;
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
      );

      Uint8List? afterBytes;
      final afterUrl = response['after_image_url'] as String?;
      final jobId = response['job_id']?.toString();
      final favorite = jobId == null ? false : await favoriteImageStore.contains(jobId);
      if (afterUrl != null) {
        rawAfterBytes = await widget.api.fetchImage(afterUrl);
        afterBytes = await PhotoLookService.apply(rawAfterBytes!, selectedLook);

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
        isFavorite = favorite;
        showOriginal = false;
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

  String get _currentPlan =>
      (widget.subscription['plan']?.toString() ?? 'free').toLowerCase();

  Set<String> get _allowedMakeupStyles {
    final serverValues = widget.subscription['available_makeup_styles'];
    if (serverValues is List && serverValues.isNotEmpty) {
      return serverValues.map((item) => item.toString()).toSet();
    }
    switch (_currentPlan) {
      case 'basic':
        return const {'natural', 'soft_glam'};
      case 'pro':
      case 'enterprise':
        return _makeupStyles.keys.toSet();
      default:
        return const {'natural'};
    }
  }

  Set<String> get _allowedPhotoFinishes {
    final serverValues = widget.subscription['available_photo_finishes'];
    if (serverValues is List && serverValues.isNotEmpty) {
      return serverValues.map((item) => item.toString()).toSet();
    }
    switch (_currentPlan) {
      case 'basic':
        return const {'Natural Finish', 'Warm Glow', 'Soft Glam'};
      case 'pro':
      case 'enterprise':
        return PhotoLookService.names.toSet();
      default:
        return const {'Natural Finish', 'Warm Glow'};
    }
  }

  Future<void> _showUpgradeDialog({
    required String feature,
    required String requiredPlan,
  }) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        icon: const Icon(Icons.lock_outline_rounded, size: 34),
        title: Text('$feature is a $requiredPlan feature'),
        content: Text(
          'Your current ${_currentPlan.toUpperCase()} plan does not include this tool. '
          'Contact the MakeupArt platform administrator to activate or renew a plan. '
          'Online automatic checkout is not configured, so this app will not pretend a payment was completed.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Understood'),
          ),
        ],
      ),
    );
  }

  Future<void> _selectMakeupStyle(String style) async {
    if (!_allowedMakeupStyles.contains(style)) {
      final requiredPlan = style == 'soft_glam' ? 'Basic' : 'Pro';
      await _showUpgradeDialog(
        feature: _makeupStyles[style] ?? style,
        requiredPlan: requiredPlan,
      );
      return;
    }
    setState(() {
      selectedMakeupStyle = style;
      result = null;
      rawAfterBytes = null;
      displayedAfterBytes = null;
      afterImageFuture = null;
      showOriginal = false;
      error = null;
    });
  }

  Future<void> _selectLook(String look) async {
    if (!_allowedPhotoFinishes.contains(look)) {
      final requiredPlan = look == 'Soft Glam' ? 'Basic' : 'Pro';
      await _showUpgradeDialog(feature: look, requiredPlan: requiredPlan);
      return;
    }
    setState(() {
      selectedLook = look;
      error = null;
    });
    final raw = rawAfterBytes;
    if (raw == null) return;

    setState(() => loading = true);
    try {
      final styled = await PhotoLookService.apply(raw, look);
      if (!mounted) return;
      setState(() {
        displayedAfterBytes = styled;
        showOriginal = false;
        afterImageFuture = Future<Uint8List>.value(styled);
      });
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Could not apply this photo finish.');
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _toggleFavorite() async {
    final bytes = displayedAfterBytes;
    final jobId = result?['job_id']?.toString();
    if (bytes == null || bytes.isEmpty || jobId == null || savingFavorite) return;

    setState(() {
      savingFavorite = true;
      error = null;
    });
    try {
      if (isFavorite) {
        await favoriteImageStore.remove(jobId);
        if (mounted) {
          setState(() => isFavorite = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Removed from favorites.')),
          );
        }
      } else {
        await favoriteImageStore.save(bytes, jobId: jobId);
        if (mounted) {
          setState(() => isFavorite = true);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Saved to private on-device favorites.'),
            ),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not update favorites on this device.')),
        );
      }
    } finally {
      if (mounted) setState(() => savingFavorite = false);
    }
  }

  Future<void> _shareResult() async {
    final bytes = displayedAfterBytes;
    if (bytes == null || bytes.isEmpty || sharingResult) return;

    final promotionController = TextEditingController();
    final promotion = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Share beauty result'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Add an optional product, offer, or booking message to promote your salon.',
            ),
            const SizedBox(height: 12),
            TextField(
              controller: promotionController,
              maxLines: 3,
              maxLength: 240,
              decoration: const InputDecoration(
                labelText: 'Product / offer caption (optional)',
                hintText: 'e.g. Bridal makeover bookings open this week',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(
              promotionController.text.trim(),
            ),
            child: const Text('Continue to share'),
          ),
        ],
      ),
    );
    promotionController.dispose();
    if (promotion == null || !mounted) return;

    setState(() => sharingResult = true);
    try {
      Map<String, dynamic> salon = const {};
      try {
        salon = await widget.api.getSalonProfile();
      } catch (_) {
        // Sharing still works when a profile refresh is temporarily unavailable.
      }
      final salonName = salon['name']?.toString().trim().isNotEmpty == true
          ? salon['name'].toString().trim()
          : 'our salon';
      final captionParts = <String>[
        if (promotion.isNotEmpty) promotion,
        'Beauty look by $salonName.',
        if (salon['phone']?.toString().trim().isNotEmpty == true)
          'Bookings: ${salon['phone']}',
        if (salon['instagram']?.toString().trim().isNotEmpty == true)
          'Instagram: ${salon['instagram'].toString().startsWith('@') ? salon['instagram'] : '@${salon['instagram']}'}',
        if (salon['tiktok']?.toString().trim().isNotEmpty == true)
          'TikTok: ${salon['tiktok'].toString().startsWith('@') ? salon['tiktok'] : '@${salon['tiktok']}'}',
        'Made with MakeupArt V8.',
      ];
      await ShareImageService.sharePng(
        bytes: bytes,
        fileName: 'makeupart_${DateTime.now().millisecondsSinceEpoch}.png',
        caption: captionParts.join('\n'),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Share sheet opened. Choose a social app to publish the result.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Could not open the share sheet. Try saving the image instead.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() => sharingResult = false);
    }
  }

  Future<void> _openFavorites() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => FavoritesPage(salonId: widget.salonId),
      ),
    );
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
    final canProcess = selected != null &&
        consentConfirmed &&
        !loading &&
        (customerId == null || customerConsentActive == true);

    return Scaffold(
      appBar: AppBar(
        title: const Text('MakeupArt Studio'),
        actions: [
          IconButton(
            tooltip: 'Settings, plan, privacy, and branding',
            onPressed: loading
                ? null
                : () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => SettingsPage(
                          api: widget.api,
                          salonId: widget.salonId,
                          subscription: widget.subscription,
                          canManageBranding: widget.canManageBranding,
                        ),
                      ),
                    ),
            icon: const Icon(Icons.settings_outlined),
          ),
          IconButton(
            tooltip: 'Favorite results',
            onPressed: _openFavorites,
            icon: const Icon(Icons.favorite_border_rounded),
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
                      'The 10 latest AI results stay in the app. Older results are moved to phone storage automatically.',
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
                    'Makeup style',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'Choose the lip tint and cheek-blush finish applied to the detected face.',
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: _makeupStyles.entries.map((style) {
                      return ChoiceChip(
                        avatar: const Icon(
                          Icons.face_retouching_natural_rounded,
                          size: 17,
                        ),
                        label: Text(style.value),
                        selected: selectedMakeupStyle == style.key,
                        onSelected: loading ? null : (_) => _selectMakeupStyle(style.key),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    'Photo finish',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 5),
                  const Text(
                    'These are final-image color grades. Eyeliner, eyeshadow, and hairstyle generation are not yet supported by the current AI engine.',
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: PhotoLookService.names.map((look) {
                      return ChoiceChip(
                        avatar: Icon(
                          !_allowedPhotoFinishes.contains(look)
                              ? Icons.lock_outline_rounded
                              : selectedLook == look
                                  ? Icons.check_circle_rounded
                                  : Icons.auto_awesome_outlined,
                          size: 17,
                        ),
                        label: Text(look),
                        selected: selectedLook == look,
                        onSelected: loading ? null : (_) => _selectLook(look),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 16),
                  Text('Skin polish strength ${(intensity * 100).round()}%'),
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
                      'Makeup style: ${_makeupStyles[selectedMakeupStyle] ?? selectedMakeupStyle}',
                    ),
                    Text(
                      'Image structure preservation score: ${result!['identity_similarity']}',
                    ),
                    Text('Skin tone: ${result!['skin_tone']}'),
                    Text('Undertone: ${result!['undertone']}'),
                    Text('Foundation match estimate: ${result!['foundation_match']}'),
                    const SizedBox(height: 14),
                    SegmentedButton<bool>(
                      segments: const [
                        ButtonSegment<bool>(
                          value: true,
                          icon: Icon(Icons.image_outlined),
                          label: Text('Before'),
                        ),
                        ButtonSegment<bool>(
                          value: false,
                          icon: Icon(Icons.auto_awesome_rounded),
                          label: Text('After'),
                        ),
                      ],
                      selected: <bool>{showOriginal},
                      onSelectionChanged: loading
                          ? null
                          : (selection) => setState(
                                () => showOriginal = selection.first,
                              ),
                    ),
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
                          final imageWidget = showOriginal && selected != null
                              ? Image.file(
                                  File(selected!.path),
                                  fit: BoxFit.contain,
                                  errorBuilder: (_, __, ___) => const Icon(
                                    Icons.broken_image_outlined,
                                    size: 48,
                                  ),
                                )
                              : Image.memory(
                                  snapshot.data!,
                                  fit: BoxFit.contain,
                                  errorBuilder: (_, __, ___) => const Icon(
                                    Icons.broken_image_outlined,
                                    size: 48,
                                  ),
                                );
                          return ClipRRect(
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              width: double.infinity,
                              constraints: const BoxConstraints(minHeight: 180, maxHeight: 460),
                              alignment: Alignment.center,
                              color: const Color(0xFF10131D),
                              padding: const EdgeInsets.all(6),
                              child: imageWidget,
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
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: savingFavorite || loading ? null : _toggleFavorite,
                              icon: savingFavorite
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : Icon(isFavorite
                                      ? Icons.favorite_rounded
                                      : Icons.favorite_border_rounded),
                              label: Text(
                                savingFavorite
                                    ? 'Saving...'
                                    : isFavorite
                                        ? 'Remove favorite'
                                        : 'Add favorite',
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: FilledButton.tonalIcon(
                              onPressed: sharingResult || loading ? null : _shareResult,
                              icon: sharingResult
                                  ? const SizedBox(
                                      width: 16,
                                      height: 16,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.share_rounded),
                              label: Text(sharingResult ? 'Opening...' : 'Share result'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'The PNG includes the salon watermark. Sharing opens your phone’s share sheet with an optional promotional caption.',
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
