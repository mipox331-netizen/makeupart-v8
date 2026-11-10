import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';
import '../services/beauty_error_message.dart';
import '../services/photo_look_service.dart';
import '../services/recent_image_store.dart';
import '../services/salon_look_preset_store.dart';
import '../widgets/before_after_comparison.dart';
import '../widgets/developer_branding.dart';
import '../widgets/face_sample_artwork.dart';
import 'admin_portal_login_page.dart';
import 'settings_page.dart';

class BeautyPage extends StatefulWidget {
  const BeautyPage({
    super.key,
    required this.api,
    required this.onLogout,
    required this.salonId,
    this.canManageBranding = false,
    this.lookPresetStore,
    this.onAdminPortalAuthenticated,
  });

  final ApiClient api;
  final VoidCallback onLogout;
  final String salonId;
  final bool canManageBranding;
  final SalonLookPresetStore? lookPresetStore;
  final VoidCallback? onAdminPortalAuthenticated;

  @override
  State<BeautyPage> createState() => _BeautyPageState();
}

class _BeautyPageState extends State<BeautyPage> with WidgetsBindingObserver {
  final picker = ImagePicker();
  final ScrollController _editorScrollController = ScrollController();

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
    'skin_only': 'Skin Polish Only',
  };

  // Folder order mirrors a familiar face editor. Local folders use real
  // MediaPipe/OpenCV operations; hairstyles remain provider-gated.
  static const _faceEditorFolderOrder = <String>[
    'Impression',
    'Skin',
    'Sizes',
    'Hairstyles',
    'Hair Colors',
    'Smiles',
    'Features',
    'Beards',
    'Makeup',
    'Age',
    'Gender',
    'Glasses',
  ];

  static const _faceFilterFolderIcons = <String, IconData>{
    'Impression': Icons.auto_awesome_rounded,
    'Skin': Icons.spa_outlined,
    'Sizes': Icons.aspect_ratio_rounded,
    'Hairstyles': Icons.content_cut_rounded,
    'Hair Colors': Icons.palette_outlined,
    'Smiles': Icons.sentiment_satisfied_alt_rounded,
    'Features': Icons.face_retouching_natural_rounded,
    'Beards': Icons.face_rounded,
    'Makeup': Icons.brush_outlined,
    'Age': Icons.hourglass_empty_rounded,
    'Gender': Icons.person_outline_rounded,
    'Glasses': Icons.visibility_outlined,
  };

  static const _faceFilterFolderDescriptions = <String, String>{
    'Impression': 'Warm tones and photo finishes',
    'Skin': 'Smooth and balance the portrait',
    'Sizes': 'Subtle face-shape refinements',
    'Hairstyles': 'Try a different hairstyle with generative AI',
    'Hair Colors': 'Preview hair color locally',
    'Smiles': 'Lift the smile naturally',
    'Features': 'Refine facial proportions',
    'Beards': 'Preview facial-hair styles',
    'Makeup': 'Eyes, lips, cheeks and complete looks',
    'Age': 'Youthful skin or a mature wrinkle finish',
    'Gender': 'Feminine or masculine presentation styles',
    'Glasses': 'Try different frame styles',
  };

  static const _faceEditOptions = <String, List<String>>{
    'Hair Colors': ['hair_black', 'hair_brown', 'hair_auburn', 'hair_blonde'],
    'Smiles': ['soft_smile'],
    'Sizes': ['slim_face', 'v_shape'],
    'Features': ['slim_face', 'v_shape'],
    'Beards': ['stubble', 'short_beard', 'full_beard', 'mustache'],
    'Age': ['youthful_finish', 'age_mature'],
    'Gender': ['feminine_presentation', 'masculine_presentation'],
    'Glasses': ['glasses_round', 'glasses_square', 'glasses_aviator'],
  };

  static const _faceEditNames = <String, String>{
    'hair_black': 'Natural Black',
    'hair_brown': 'Chocolate Brown',
    'hair_auburn': 'Auburn',
    'hair_blonde': 'Golden Blonde',
    'soft_smile': 'Soft Smile',
    'slim_face': 'Slim Face',
    'v_shape': 'V-Shape',
    'stubble': 'Light Stubble',
    'short_beard': 'Short Beard',
    'full_beard': 'Full Beard',
    'mustache': 'Mustache',
    'youthful_finish': 'Youthful Finish',
    'age_mature': 'Mature Finish',
    'feminine_presentation': 'Feminine Style',
    'masculine_presentation': 'Masculine Style',
    'glasses_round': 'Round Frames',
    'glasses_square': 'Square Frames',
    'glasses_aviator': 'Aviator Frames',
  };

  static const _faceEditDescriptions = <String, String>{
    'hair_black': 'Darken visible hair to a natural black tone',
    'hair_brown': 'Add a chocolate-brown hair tint',
    'hair_auburn': 'Add a warm auburn hair tint',
    'hair_blonde': 'Preview a golden-blonde hair tone',
    'soft_smile': 'Gently lift the mouth corners',
    'slim_face': 'Apply a subtle cheek-slimming warp',
    'v_shape': 'Refine the lower-face contour',
    'stubble': 'Add a light beard shadow',
    'short_beard': 'Preview a short beard',
    'full_beard': 'Preview a fuller beard overlay',
    'mustache': 'Add a subtle mustache overlay',
    'youthful_finish': 'Smooth facial texture while preserving detail',
    'age_mature': 'Add a subtle fine-line mature finish',
    'feminine_presentation': 'Apply soft blush and lip styling',
    'masculine_presentation': 'Apply a light beard and brow styling',
    'glasses_round': 'Round optical frames',
    'glasses_square': 'Square optical frames',
    'glasses_aviator': 'Aviator-style frames',
  };

  static const _faceEditIcons = <String, IconData>{
    'hair_black': Icons.palette_outlined,
    'hair_brown': Icons.palette_outlined,
    'hair_auburn': Icons.palette_outlined,
    'hair_blonde': Icons.palette_outlined,
    'soft_smile': Icons.sentiment_satisfied_alt_rounded,
    'slim_face': Icons.face_retouching_natural_rounded,
    'v_shape': Icons.face_retouching_natural_rounded,
    'stubble': Icons.face_rounded,
    'short_beard': Icons.face_rounded,
    'full_beard': Icons.face_rounded,
    'mustache': Icons.face_rounded,
    'youthful_finish': Icons.spa_outlined,
    'age_mature': Icons.hourglass_empty_rounded,
    'feminine_presentation': Icons.auto_awesome_rounded,
    'masculine_presentation': Icons.person_outline_rounded,
    'glasses_round': Icons.visibility_outlined,
    'glasses_square': Icons.visibility_outlined,
    'glasses_aviator': Icons.visibility_outlined,
  };

  static const _hairLookKeys = <String>{
    'sleek_hair',
    'soft_curls',
    'braided_style',
    'elegant_updo',
  };
  static const _classicStyleCategories = <String, List<String>>{
    'Looks': ['natural', 'soft_glam', 'bridal_rose', 'evening_glam'],
    'Eyes': ['smokey_eye', 'cat_eye', 'eyeshadow', 'eyeliner'],
    'Lips & cheeks': ['lipstick', 'blush'],
  };

  static const _generativeLookCategories = <String, List<String>>{
    'Looks': ['natural', 'soft_glam', 'full_glam', 'bridal_glam', 'editorial'],
    'Eyes': ['smokey_eye', 'cat_eye', 'eyeshadow', 'eyeliner'],
    'Lips & cheeks': ['lipstick', 'blush'],
    'Skin': ['foundation'],
    'Hair': ['sleek_hair', 'soft_curls', 'braided_style', 'elegant_updo'],
  };

  static const _categoryIcons = <String, IconData>{
    'Looks': Icons.auto_awesome_rounded,
    'Eyes': Icons.visibility_outlined,
    'Lips & cheeks': Icons.palette_outlined,
    'Skin': Icons.layers_outlined,
    'Hair': Icons.content_cut_rounded,
  };

  static const _makeupStyleIcons = <String, IconData>{
    'natural': Icons.spa_outlined,
    'soft_glam': Icons.auto_awesome_rounded,
    'bridal_rose': Icons.favorite_border_rounded,
    'evening_glam': Icons.nights_stay_rounded,
    'smokey_eye': Icons.visibility_outlined,
    'cat_eye': Icons.remove_red_eye_outlined,
    'eyeshadow': Icons.palette_outlined,
    'eyeliner': Icons.edit_outlined,
    'lipstick': Icons.color_lens_outlined,
    'blush': Icons.brush_outlined,
    'skin_only': Icons.spa_outlined,
  };

  static const _makeupStyleDescriptions = <String, String>{
    'natural': 'Everyday look',
    'soft_glam': 'Softly defined',
    'bridal_rose': 'Wedding-ready',
    'evening_glam': 'Bold evening look',
    'smokey_eye': 'Smoky eye effect',
    'cat_eye': 'Winged eye effect',
    'eyeshadow': 'Eye color',
    'eyeliner': 'Eye definition',
    'lipstick': 'Lip color',
    'blush': 'Cheek color',
    'skin_only': 'Skin polish without cosmetic overlays',
  };

  static const _generativeLookIcons = <String, IconData>{
    'natural': Icons.spa_outlined,
    'soft_glam': Icons.auto_awesome_outlined,
    'full_glam': Icons.stars_rounded,
    'bridal_glam': Icons.favorite_border_rounded,
    'smokey_eye': Icons.visibility_outlined,
    'cat_eye': Icons.remove_red_eye_outlined,
    'eyeshadow': Icons.palette_outlined,
    'eyeliner': Icons.edit_outlined,
    'lipstick': Icons.color_lens_outlined,
    'blush': Icons.brush_outlined,
    'foundation': Icons.layers_outlined,
    'editorial': Icons.photo_camera_outlined,
    'sleek_hair': Icons.content_cut_rounded,
    'soft_curls': Icons.waves_rounded,
    'braided_style': Icons.account_tree_outlined,
    'elegant_updo': Icons.style_outlined,
  };

  static const _generativeLookDescriptions = <String, String>{
    'natural': 'Natural everyday look',
    'soft_glam': 'Soft definition',
    'full_glam': 'Full makeup look',
    'bridal_glam': 'Bridal makeup',
    'smokey_eye': 'Smoky eye makeup',
    'cat_eye': 'Winged eye makeup',
    'eyeshadow': 'Eye makeup',
    'eyeliner': 'Eye definition',
    'lipstick': 'Lip color',
    'blush': 'Cheek color',
    'foundation': 'Skin base',
    'editorial': 'Fashion editorial',
    'sleek_hair': 'Sleek hairstyle',
    'soft_curls': 'Soft curls',
    'braided_style': 'Braided hairstyle',
    'elegant_updo': 'Elegant updo',
  };

  static const _photoFinishIcons = <String, IconData>{
    'Natural Finish': Icons.tune_rounded,
    'Warm Glow': Icons.wb_sunny_outlined,
    'Soft Glam': Icons.auto_awesome_outlined,
    'Studio Polish': Icons.camera_alt_outlined,
    'Golden Hour': Icons.light_mode_rounded,
  };

  static const _photoFinishDescriptions = <String, String>{
    'Natural Finish': 'True-to-life color',
    'Warm Glow': 'Warm, sunny tone',
    'Soft Glam': 'Gentle contrast',
    'Studio Polish': 'Clean studio tone',
    'Golden Hour': 'Golden warmth',
  };


  RecentImageStore get recentImageStore =>
      RecentImageStore(scope: widget.salonId);

  SalonLookPresetStore get _lookPresetStore =>
      widget.lookPresetStore ?? SalonLookPresetStore(scope: widget.salonId);

  XFile? selected;
  Map<String, dynamic>? result;
  Future<Uint8List>? afterImageFuture;
  Uint8List? rawAfterBytes;
  Uint8List? displayedAfterBytes;
  Uint8List? faceAppComparisonBytes;
  bool loadingFaceAppComparison = false;
  String selectedLook = 'Natural Finish';
  String selectedMakeupStyle = 'natural';
  String selectedFaceEffect = 'none';
  String? _selectedFilterFolder;
  final GlobalKey _filterToolsAnchorKey = GlobalKey();
  String _selectedClassicCategory = 'Looks';
  String _selectedGenerativeCategory = 'Looks';
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
  bool updatingStoredConsent = false;
  double intensity = 0.7;
  double brightness = 0.0;
  double contrast = 1.0;
  double saturation = 1.0;
  double warmth = 0.0;
  double sharpness = 0.0;
  bool loading = false;
  bool loadingCustomers = true;
  bool consentConfirmed = false;
  String? error;
  List<File> recentImages = [];
  List<SalonLookPreset> savedLookPresets = [];
  bool loadingSavedLookPresets = true;
  bool savingLookPreset = false;
  bool _phoneBackupInProgress = false;

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _editorScrollController.dispose();
    super.dispose();
  }

  Future<void> _openMrAiDashboard() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => AdminPortalLoginPage(
          api: widget.api,
          onLoggedIn: () {
            widget.onAdminPortalAuthenticated?.call();
            Navigator.of(context).pop();
          },
        ),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadCustomers();
    _loadRecentImages();
    _loadSavedLookPresets();
    _loadCapabilities();
    _loadSubscription();
    // Retry phone-gallery copies without blocking the editor or showing a
    // backup banner. This recovers results whose previous MediaStore write
    // failed (for example, when the phone was temporarily out of storage).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _retryPhonePhotoBackupSilently();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _retryPhonePhotoBackupSilently();
    }
  }

  Future<void> _retryPhonePhotoBackupSilently() async {
    if (!Platform.isAndroid || _phoneBackupInProgress) return;
    _phoneBackupInProgress = true;
    try {
      // GalleryExporter uses deterministic salon-scoped filenames, so this
      // safely updates existing copies instead of creating duplicates.
      await recentImageStore.backupAllToGallery();
    } catch (_) {
      // Never interrupt the editing experience. The private app copy remains
      // available and the next app open/resume retries the Gallery write.
    } finally {
      _phoneBackupInProgress = false;
    }
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
      // Keep UI entitlements conservative while the subscription API is unreachable.
      // A successful reload restores the current plan and exact feature list.
      if (mounted) setState(() => subscription = {});
    } finally {
      if (mounted) setState(() => loadingSubscription = false);
    }
  }

  List<String> _availableOptions(String key, List<String> fallback) {
    final value = subscription[key];
    if (value is List) return value.whereType<String>().toList();

    // Keep the UI conservative if subscription data cannot be loaded.
    // The backend remains authoritative and enforces plan entitlements.
    final plan = (subscription['plan']?.toString() ?? 'free').toLowerCase();
    if (key == 'available_makeup_styles') {
      switch (plan) {
        case 'basic':
          return const ['natural', 'soft_glam', 'skin_only'];
        case 'pro':
        case 'enterprise':
          return fallback;
        default:
          return const ['natural', 'skin_only'];
      }
    }
    if (key == 'available_photo_finishes') {
      switch (plan) {
        case 'basic':
          return const ['Natural Finish', 'Warm Glow', 'Soft Glam'];
        case 'pro':
        case 'enterprise':
          return fallback;
        default:
          return const ['Natural Finish', 'Warm Glow'];
      }
    }
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
      faceAppComparisonBytes = null;
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
      final isActive = consent != null;
      setState(() {
        if (customerConsentActive != isActive) {
          customerConsentActive = isActive;
          // A consent change invalidates all previous confirmations and outputs.
          consentConfirmed = false;
          externalAiConsentConfirmed = false;
          _clearProcessedResult();
        }
      });
    } catch (_) {
      // An older client's failed request must never overwrite the current client's state.
      if (!mounted || customerId != id) return;
      setState(() {
        if (customerConsentActive != false) {
          customerConsentActive = false;
          consentConfirmed = false;
          externalAiConsentConfirmed = false;
          _clearProcessedResult();
        }
      });
    }
  }

  Future<void> _toggleStoredConsent() async {
    final id = customerId;
    if (id == null || updatingStoredConsent) return;
    final grant = customerConsentActive != true;
    setState(() => updatingStoredConsent = true);
    try {
      await widget.api.setCustomerConsent(customerId: id, granted: grant);
      // The operator may switch clients while the consent request is in flight.
      if (!mounted || customerId != id) return;
      setState(() {
        // A grant/revocation changes the consent state; require a fresh operator confirmation.
        consentConfirmed = false;
        externalAiConsentConfirmed = false;
        _clearProcessedResult();
      });
      await _refreshCustomerConsent(id);
    } catch (_) {
      if (mounted && customerId == id) {
        setState(() => error = 'Could not update client consent.');
      }
    } finally {
      if (mounted) setState(() => updatingStoredConsent = false);
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
        faceAppComparisonBytes = null;
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
        faceAppComparisonBytes = null;
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
        faceEdit: _faceEditOptions.containsKey(_selectedFilterFolder)
            ? selectedFaceEffect
            : 'none',
        photoFinish: selectedLook,
        engine: selectedEngine,
        generativeLook: selectedGenerativeLook,
        externalAiConsent: externalAiConsentConfirmed,
        brightness: brightness,
        contrast: contrast,
        saturation: saturation,
        warmth: warmth,
        sharpness: sharpness,
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
      setState(() => error = beautyProcessingErrorMessage(exception));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  void _clearProcessedResult() {
    result = null;
    afterImageFuture = null;
    rawAfterBytes = null;
    displayedAfterBytes = null;
    faceAppComparisonBytes = null;
    error = null;
  }

  String _filterFolderStatus(String folder) {
    switch (folder) {
      case 'Impression':
      case 'Skin':
      case 'Makeup':
      case 'Sizes':
      case 'Hair Colors':
      case 'Smiles':
      case 'Features':
      case 'Beards':
      case 'Age':
      case 'Gender':
      case 'Glasses':
        return 'AVAILABLE';
      case 'Hairstyles':
        if (loadingCapabilities || loadingSubscription) return 'CHECKING';
        if (capabilities['generative_available'] != true) return 'AI NOT READY';
        if (subscription['generative_engine_entitled'] != true) return 'PRO REQUIRED';
        return 'GENERATIVE AI';
      default:
        return 'COMING SOON';
    }
  }

  bool _canProcessSelectedFolder() {
    const supportedFolders = {
      'Impression',
      'Skin',
      'Makeup',
      'Hairstyles',
      'Sizes',
      'Hair Colors',
      'Smiles',
      'Features',
      'Beards',
      'Age',
      'Gender',
      'Glasses',
    };
    if (!supportedFolders.contains(_selectedFilterFolder)) return false;
    if (_selectedFilterFolder == 'Hairstyles') {
      return generativeAvailable && selectedEngine == 'generative';
    }
    return true;
  }

  void _openFilterFolder(String folder) {
    setState(() {
      // A result belongs to the folder and options used to create it. Clear it
      // whenever the user changes folders, including roadmap-only folders.
      if (_selectedFilterFolder != folder) {
        _clearProcessedResult();
      }
      _selectedFilterFolder = folder;

      if (folder == 'Impression' || folder == 'Skin') {
        final changed = selectedEngine != 'classic' ||
            selectedMakeupStyle != 'skin_only';
        selectedEngine = 'classic';
        selectedMakeupStyle = 'skin_only';
        selectedFaceEffect = 'none';
        externalAiConsentConfirmed = false;
        if (changed) _clearProcessedResult();
      } else if (folder == 'Makeup') {
        selectedFaceEffect = 'none';
        if (selectedEngine == 'generative') {
          if (_hairLookKeys.contains(selectedGenerativeLook) ||
              selectedGenerativeLook == 'foundation') {
            selectedGenerativeLook = 'full_glam';
            externalAiConsentConfirmed = false;
            _clearProcessedResult();
          }
          if (_selectedGenerativeCategory == 'Hair' ||
              _selectedGenerativeCategory == 'Skin') {
            _selectedGenerativeCategory = 'Looks';
          }
        } else if (selectedMakeupStyle == 'skin_only') {
          selectedMakeupStyle = 'natural';
          _clearProcessedResult();
        }
      } else if (folder == 'Hairstyles') {
        final changed = selectedEngine != 'generative' ||
            !_hairLookKeys.contains(selectedGenerativeLook) ||
            selectedFaceEffect != 'none';
        selectedEngine = 'generative';
        selectedFaceEffect = 'none';
        if (!_hairLookKeys.contains(selectedGenerativeLook)) {
          selectedGenerativeLook = 'soft_curls';
        }
        _selectedGenerativeCategory = 'Hair';
        if (changed) {
          externalAiConsentConfirmed = false;
          _clearProcessedResult();
        }
      } else if (_faceEditOptions.containsKey(folder)) {
        final options = _faceEditOptions[folder]!;
        final changed = selectedEngine != 'classic' ||
            selectedFaceEffect != options.first ||
            selectedMakeupStyle != 'natural' ||
            selectedLook != 'Natural Finish';
        selectedEngine = 'classic';
        selectedMakeupStyle = 'natural';
        selectedLook = 'Natural Finish';
        selectedFaceEffect = options.first;
        externalAiConsentConfirmed = false;
        if (changed) _clearProcessedResult();
      } else {
        selectedEngine = 'classic';
        selectedFaceEffect = 'none';
      }
    });

    _scrollToFilterTools();
  }

  void _scrollToFilterTools() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final target = _filterToolsAnchorKey.currentContext;
      if (target == null || !target.mounted) return;
      Scrollable.ensureVisible(
        target,
        alignment: 0.08,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeOutCubic,
      );
    });
  }

  void _selectEngine(String engine) {
    if (engine == 'generative' && !generativeAvailable) return;
    setState(() {
      selectedEngine = engine;
      if (engine == 'generative') {
        if (_selectedFilterFolder != 'Hairstyles') {
          _selectedFilterFolder = 'Makeup';
        }
        if (_hairLookKeys.contains(selectedGenerativeLook) ||
            selectedGenerativeLook == 'foundation') {
          selectedGenerativeLook = 'full_glam';
        }
        _selectedGenerativeCategory = 'Looks';
      } else if (_selectedFilterFolder == 'Hairstyles') {
        // Classic AI cannot render new hairstyles, so take the user to a
        // folder that the selected engine can actually process.
        _selectedFilterFolder = 'Makeup';
        if (selectedMakeupStyle == 'skin_only') {
          selectedMakeupStyle = 'natural';
        }
      }
      externalAiConsentConfirmed = false;
      _clearProcessedResult();
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
      faceAppComparisonBytes = null;
      error = null;
    });
  }

  Future<void> _chooseFaceAppComparison() async {
    if (displayedAfterBytes == null || loadingFaceAppComparison) return;
    setState(() => loadingFaceAppComparison = true);
    try {
      final image = await picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 95,
      );
      if (image == null) return;
      final bytes = await image.readAsBytes();
      if (bytes.isEmpty) {
        throw const FormatException('Selected FaceApp image is empty.');
      }
      if (!mounted) return;
      setState(() => faceAppComparisonBytes = bytes);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Haikuweza kusoma picha ya FaceApp kutoka Gallery.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) setState(() => loadingFaceAppComparison = false);
    }
  }

  Future<void> _saveResultToGallery() async {
    final bytes = displayedAfterBytes;
    if (bytes == null || bytes.isEmpty || savingGallery) return;

    setState(() {
      savingGallery = true;
      error = null;
    });
    try {
      final localFile = await recentImageStore.save(
        bytes,
        jobId: result?['job_id']?.toString(),
      );
      // save() makes the automatic attempt; this verified retry lets the UI
      // report a failure instead of claiming success when Gallery was full.
      await recentImageStore.backupFileToGallery(localFile);
      await _loadRecentImages();
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


  Future<void> _loadSavedLookPresets() async {
    try {
      final presets = await _lookPresetStore.list();
      if (!mounted) return;
      setState(() => savedLookPresets = presets);
    } catch (_) {
      // Preset storage is optional; a storage problem must not block photo editing.
      if (mounted) setState(() => savedLookPresets = []);
    } finally {
      if (mounted) setState(() => loadingSavedLookPresets = false);
    }
  }

  String _suggestedPresetName() {
    switch (_selectedFilterFolder) {
      case 'Impression':
        return selectedLook;
      case 'Skin':
        return 'Skin Polish';
      case 'Hairstyles':
        return _generativeLooks[selectedGenerativeLook] ?? 'Salon Hair';
      case 'Hair Colors':
      case 'Smiles':
      case 'Sizes':
      case 'Features':
      case 'Beards':
      case 'Age':
      case 'Gender':
      case 'Glasses':
        return _faceEditNames[selectedFaceEffect] ?? 'Face Edit';
      case 'Makeup':
        return selectedEngine == 'generative'
            ? (_generativeLooks[selectedGenerativeLook] ?? 'AI Makeup')
            : (_makeupStyles[selectedMakeupStyle] ?? 'Makeup');
      default:
        return 'My Salon Look';
    }
  }

  Future<void> _saveCurrentLookPreset() async {
    final folder = _selectedFilterFolder;
    if (folder == null || !_canProcessSelectedFolder()) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Open a supported filter folder before saving a look.')),
      );
      return;
    }

    final availableStyles = _availableOptions(
      'available_makeup_styles',
      _makeupStyles.keys.toList(),
    );
    final availableFinishes = _availableOptions(
      'available_photo_finishes',
      PhotoLookService.names,
    );
    if ((folder == 'Skin' || folder == 'Impression') &&
        !availableStyles.contains('skin_only')) {
      _showPlanRequired('Pro', 'Skin Polish');
      return;
    }
    if (!availableFinishes.contains(selectedLook)) {
      _showPlanRequired(selectedLook == 'Soft Glam' ? 'Basic' : 'Pro', selectedLook);
      return;
    }
    if (folder == 'Makeup' && selectedEngine == 'classic' &&
        !availableStyles.contains(selectedMakeupStyle)) {
      _showPlanRequired(
        selectedMakeupStyle == 'soft_glam' ? 'Basic' : 'Pro',
        _makeupStyles[selectedMakeupStyle] ?? selectedMakeupStyle,
      );
      return;
    }
    if ((folder == 'Makeup' || folder == 'Hairstyles') &&
        selectedEngine == 'generative' && !generativeAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Generative AI is not configured for this salon yet.')),
      );
      return;
    }

    final suggestedName = _suggestedPresetName();
    var enteredName = suggestedName;
    final name = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Save salon look'),
        content: TextFormField(
          key: const ValueKey('salon-look-name-field'),
          initialValue: suggestedName,
          autofocus: true,
          maxLength: SalonLookPresetStore.maxNameLength,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(
            labelText: 'Look name',
            hintText: 'e.g. Bridal Glow',
          ),
          onChanged: (value) => enteredName = value,
          onFieldSubmitted: (value) => Navigator.of(dialogContext).pop(value),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            key: const ValueKey('save-salon-look-confirm'),
            onPressed: () => Navigator.of(dialogContext).pop(enteredName),
            child: const Text('Save look'),
          ),
        ],
      ),
    );
    if (name == null || !mounted) return;

    setState(() => savingLookPreset = true);
    try {
      await _lookPresetStore.save(
        name: name,
        folder: folder,
        engine: selectedEngine,
        makeupStyle: selectedMakeupStyle,
        faceEdit: selectedFaceEffect,
        generativeLook: selectedGenerativeLook,
        photoFinish: selectedLook,
        intensity: intensity,
        brightness: brightness,
        contrast: contrast,
        saturation: saturation,
        warmth: warmth,
        sharpness: sharpness,
      );
      await _loadSavedLookPresets();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Saved “${name.trim()}” to this salon on this device.')),
      );
    } catch (exception) {
      if (!mounted) return;
      final message = exception is SalonLookPresetLimitException
          ? exception.message
          : 'Could not save this look on the device.';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    } finally {
      if (mounted) setState(() => savingLookPreset = false);
    }
  }

  void _applyLookPreset(SalonLookPreset preset) {
    // Saved settings are untrusted historical input: a preset created while a
    // salon had Pro access must not bypass the current server-provided plan.
    final availableStyles = _availableOptions(
      'available_makeup_styles',
      _makeupStyles.keys.toList(),
    );
    final availableFinishes = _availableOptions(
      'available_photo_finishes',
      PhotoLookService.names,
    );

    if (!availableFinishes.contains(preset.photoFinish)) {
      _showPlanRequired(
        preset.photoFinish == 'Soft Glam' ? 'Basic' : 'Pro',
        preset.photoFinish,
      );
      return;
    }
    if ((preset.folder == 'Skin' || preset.folder == 'Impression') &&
        !availableStyles.contains('skin_only')) {
      _showPlanRequired('Pro', 'Skin Polish');
      return;
    }
    if (preset.folder == 'Makeup' &&
        preset.engine == 'classic' &&
        !availableStyles.contains(preset.makeupStyle)) {
      _showPlanRequired(
        preset.makeupStyle == 'soft_glam' ? 'Basic' : 'Pro',
        _makeupStyles[preset.makeupStyle] ?? 'this makeup style',
      );
      return;
    }
    if (preset.engine == 'generative' && !generativeAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('This saved look needs Generative AI and an eligible salon plan.'),
        ),
      );
      return;
    }

    setState(() {
      _selectedFilterFolder = preset.folder;
      selectedEngine = preset.engine;
      selectedMakeupStyle = _makeupStyles.containsKey(preset.makeupStyle)
          ? preset.makeupStyle
          : 'natural';
      selectedFaceEffect = _faceEditNames.containsKey(preset.faceEdit)
          ? preset.faceEdit
          : 'none';
      selectedGenerativeLook = _generativeLooks.containsKey(preset.generativeLook)
          ? preset.generativeLook
          : 'full_glam';
      selectedLook = PhotoLookService.names.contains(preset.photoFinish)
          ? preset.photoFinish
          : 'Natural Finish';
      intensity = preset.intensity.clamp(0.0, 1.0).toDouble();
      brightness = preset.brightness;
      contrast = preset.contrast;
      saturation = preset.saturation;
      warmth = preset.warmth;
      sharpness = preset.sharpness;
      externalAiConsentConfirmed = false;
      _selectedClassicCategory = 'Looks';
      for (final entry in _classicStyleCategories.entries) {
        if (entry.value.contains(selectedMakeupStyle)) {
          _selectedClassicCategory = entry.key;
          break;
        }
      }
      _selectedGenerativeCategory = _hairLookKeys.contains(selectedGenerativeLook)
          ? 'Hair'
          : selectedGenerativeLook == 'foundation'
              ? 'Skin'
              : 'Looks';
      _clearProcessedResult();
    });

    _scrollToFilterTools();

    if (preset.engine == 'generative' && !generativeAvailable) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Look loaded. Generative AI must be enabled before this preset can run.'),
        ),
      );
    }
  }

  Future<void> _confirmDeleteLookPreset(SalonLookPreset preset) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete saved look?'),
        content: Text('“${preset.name}” will be removed from this device for this salon.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    try {
      await _lookPresetStore.delete(preset.id);
      await _loadSavedLookPresets();
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not delete this saved look.')),
      );
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

  Widget _buildPhotoAdjustmentSlider({
    required String keyName,
    required String label,
    required String valueLabel,
    required double value,
    required double min,
    required double max,
    required int divisions,
    required ValueChanged<double> update,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(label)),
              Text(
                valueLabel,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
          Slider(
            key: ValueKey(keyName),
            value: value,
            min: min,
            max: max,
            divisions: divisions,
            onChanged: loading
                ? null
                : (next) => setState(() {
                      update(next);
                      _clearProcessedResult();
                    }),
          ),
        ],
      ),
    );
  }

  void _resetPhotoAdjustments() {
    setState(() {
      brightness = 0.0;
      contrast = 1.0;
      saturation = 1.0;
      warmth = 0.0;
      sharpness = 0.0;
      _clearProcessedResult();
    });
  }

  Widget _buildFaceEditorToolbar() {
    return Container(
      key: const ValueKey('face-filter-folders-grid'),
      decoration: const BoxDecoration(
        color: Color(0xFF17131D),
        border: Border(
          top: BorderSide(color: Color(0x24FFFFFF)),
        ),
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 112,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
            child: Row(
              children: List<Widget>.generate(_faceEditorFolderOrder.length, (index) {
                final folder = _faceEditorFolderOrder[index];
                final status = _filterFolderStatus(folder);
                final ready = status == 'AVAILABLE' || status == 'GENERATIVE AI';
                final statusLabel = switch (status) {
                  'PRO REQUIRED' => 'PRO',
                  'AI NOT READY' => 'SETUP',
                  'COMING SOON' => 'SOON',
                  _ => '',
                };
                return Padding(
                  padding: EdgeInsets.only(
                    right: index == _faceEditorFolderOrder.length - 1 ? 0 : 4,
                  ),
                  child: _FaceEditorToolItem(
                    key: ValueKey('filter-folder-$folder'),
                    title: folder,
                    icon: _faceFilterFolderIcons[folder] ?? Icons.face_retouching_natural,
                    selected: _selectedFilterFolder == folder,
                    ready: ready,
                    statusLabel: statusLabel,
                    onTap: loading ? null : () => _openFilterFolder(folder),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final portraitHeight = (MediaQuery.sizeOf(context).height * 0.44)
        .clamp(280.0, 440.0)
        .toDouble();
    final availableMakeupStyles = _availableOptions(
      'available_makeup_styles',
      _makeupStyles.keys.toList(),
    );
    final availablePhotoFinishes = _availableOptions(
      'available_photo_finishes',
      PhotoLookService.names,
    );
    final needsSkinOnly = const {'Impression', 'Skin'}
        .contains(_selectedFilterFolder);
    final selectedFolderToolsAvailable = _canProcessSelectedFolder() &&
        (selectedEngine != 'generative' || generativeAvailable) &&
        (!needsSkinOnly || availableMakeupStyles.contains('skin_only')) &&
        availablePhotoFinishes.contains(selectedLook) &&
        (_selectedFilterFolder != 'Makeup' ||
            selectedEngine == 'generative' ||
            availableMakeupStyles.contains(selectedMakeupStyle));
    final canProcess = selected != null &&
        selectedFolderToolsAvailable &&
        consentConfirmed &&
        (selectedEngine != 'generative' ||
            (generativeAvailable && externalAiConsentConfirmed)) &&
        !loadingSubscription &&
        !loading &&
        (customerId == null || customerConsentActive == true);

    Widget buildOptionRail({
      required Key railKey,
      required int itemCount,
      required Widget Function(BuildContext, int) itemBuilder,
    }) {
      return SizedBox(
        height: 148,
        child: SingleChildScrollView(
          key: railKey,
          scrollDirection: Axis.horizontal,
          child: Row(
            children: List<Widget>.generate(itemCount, (index) {
              return Padding(
                padding: const EdgeInsets.only(right: 10),
                child: SizedBox(
                  width: 154,
                  height: 148,
                  child: itemBuilder(context, index),
                ),
              );
            }),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [Color(0xFFE9AFC5), Color(0xFF8E75C5)],
                ),
                borderRadius: BorderRadius.circular(13),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFD99AB3).withValues(alpha: .22),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Stack(
                children: [
                  Center(
                    child: Text(
                      'M',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 23,
                        fontWeight: FontWeight.w900,
                        height: 1,
                        shadows: [
                          Shadow(
                            color: Colors.black.withValues(alpha: .18),
                            blurRadius: 4,
                            offset: const Offset(0, 1),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const Positioned(
                    top: 4,
                    right: 4,
                    child: Icon(Icons.auto_awesome_rounded, size: 10, color: Colors.white),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'MakeupArt',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.3,
                      ),
                ),
                Text(
                  'BEAUTY STUDIO',
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        fontSize: 8,
                        letterSpacing: 1.5,
                        fontWeight: FontWeight.w800,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          if (displayedAfterBytes != null)
            IconButton(
              tooltip: 'Save edited photo',
              onPressed: savingGallery || loading ? null : _saveResultToGallery,
              icon: const Icon(Icons.download_rounded),
            ),
          IconButton(
            tooltip: 'Settings',
            onPressed: loading
                ? null
                : () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => MakeupArtSettingsPage(
                          api: widget.api,
                          salonId: widget.salonId,
                          canManageBranding: widget.canManageBranding,
                          onLogout: widget.onLogout,
                        ),
                      ),
                    ),
            icon: const Icon(Icons.settings_outlined),
          ),
          IconButton(
            onPressed: loading ? null : _loadCustomers,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh clients',
          ),
        ],
      ),
      body: ListView(
        key: const ValueKey('beauty-editor-scroll-view'),
        controller: _editorScrollController,
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 16),
        children: [
          Card(
            key: const ValueKey('portrait-editor-canvas'),
            child: Padding(
              padding: const EdgeInsets.all(11),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'PORTRAIT PREVIEW',
                              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                    letterSpacing: 1.5,
                                    fontWeight: FontWeight.w900,
                                    color: Theme.of(context).colorScheme.primary,
                                  ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              selected == null
                                  ? 'Start with a photo'
                                  : result == null
                                      ? 'Your portrait is ready'
                                      : 'Before & after',
                              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: -0.35,
                                  ),
                            ),
                          ],
                        ),
                      ),
                      if (selected != null)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.primaryContainer,
                            borderRadius: BorderRadius.circular(99),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.check_circle_rounded,
                                size: 13,
                                color: Theme.of(context).colorScheme.onPrimaryContainer,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                'READY',
                                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 0.6,
                                    ),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Container(
                    height: portraitHeight,
                    width: double.infinity,
                    decoration: BoxDecoration(
                      color: const Color(0xFF08070D),
                      borderRadius: BorderRadius.circular(22),
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        if (selected != null && afterImageFuture != null)
                          FutureBuilder<Uint8List>(
                            future: afterImageFuture,
                            builder: (context, snapshot) {
                              if (snapshot.connectionState == ConnectionState.waiting) {
                                return const Center(
                                  child: CircularProgressIndicator(),
                                );
                              }
                              if (snapshot.hasError ||
                                  snapshot.data == null ||
                                  snapshot.data!.isEmpty) {
                                return Image.file(
                                  File(selected!.path),
                                  fit: BoxFit.contain,
                                  errorBuilder: (_, __, ___) => const Center(
                                    child: Icon(
                                      Icons.broken_image_outlined,
                                      size: 48,
                                    ),
                                  ),
                                );
                              }
                              return BeforeAfterComparison(
                                key: ValueKey(
                                  result?['job_id']?.toString() ?? selected!.path,
                                ),
                                height: portraitHeight,
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
                          )
                        else if (selected != null)
                          Image.file(
                            File(selected!.path),
                            fit: BoxFit.contain,
                            errorBuilder: (_, __, ___) => const Center(
                              child: Icon(
                                Icons.broken_image_outlined,
                                size: 52,
                              ),
                            ),
                          )
                        else
                          Stack(
                            fit: StackFit.expand,
                            children: [
                              const DecoratedBox(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                    colors: [
                                      Color(0xFF342438),
                                      Color(0xFF171523),
                                      Color(0xFF10131B),
                                    ],
                                  ),
                                ),
                              ),
                              Positioned(
                                top: -42,
                                right: -30,
                                child: Container(
                                  width: 170,
                                  height: 170,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: const Color(0xFFD99AB3).withValues(alpha: 0.12),
                                  ),
                                ),
                              ),
                              Positioned(
                                bottom: -55,
                                left: -25,
                                child: Container(
                                  width: 180,
                                  height: 180,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: const Color(0xFF8E75C5).withValues(alpha: 0.13),
                                  ),
                                ),
                              ),
                              Center(
                                child: Padding(
                                  padding: const EdgeInsets.all(24),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Container(
                                        width: 76,
                                        height: 76,
                                        decoration: BoxDecoration(
                                          color: Colors.white.withValues(alpha: 0.08),
                                          shape: BoxShape.circle,
                                          border: Border.all(
                                            color: Colors.white.withValues(alpha: 0.13),
                                          ),
                                        ),
                                        child: const Icon(
                                          Icons.face_retouching_natural_rounded,
                                          size: 38,
                                          color: Color(0xFFF2D6E2),
                                        ),
                                      ),
                                      const SizedBox(height: 16),
                                      const Text(
                                        'Your portrait goes here',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.w800,
                                          color: Colors.white,
                                        ),
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        'Choose a clear, front-facing photo to explore your salon looks.',
                                        textAlign: TextAlign.center,
                                        style: TextStyle(
                                          fontSize: 12,
                                          height: 1.4,
                                          color: Colors.white.withValues(alpha: 0.72),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              Positioned(
                                left: 14,
                                top: 14,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 10,
                                    vertical: 6,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: 0.36),
                                    borderRadius: BorderRadius.circular(99),
                                    border: Border.all(
                                      color: Colors.white.withValues(alpha: 0.14),
                                    ),
                                  ),
                                  child: const Text(
                                    'MAKEUPART STUDIO',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 9,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 1.1,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        if (selected != null && afterImageFuture == null)
                          Positioned(
                            left: 12,
                            top: 12,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.62),
                                borderRadius: BorderRadius.circular(99),
                              ),
                              child: const Text(
                                'ORIGINAL',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 9,
                                  fontWeight: FontWeight.w900,
                                  letterSpacing: 1,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.tonalIcon(
                          onPressed: loading ? null : () => pick(ImageSource.gallery),
                          icon: const Icon(Icons.photo_library_outlined),
                          label: const Text('Gallery'),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(0, 52),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: loading ? null : () => pick(ImageSource.camera),
                          icon: const Icon(Icons.camera_alt_outlined),
                          label: const Text('Camera'),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(0, 52),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
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
                          onPressed: loading || updatingStoredConsent
                              ? null
                              : _toggleStoredConsent,
                          child: Text(
                            updatingStoredConsent
                                ? 'Saving...'
                                : customerConsentActive == true
                                    ? 'Revoke'
                                    : 'Grant',
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 20),
                  const _EditorSectionHeading(
                    step: '03',
                    title: 'Choose an editing engine',
                    subtitle: 'Classic edits are ready. Generative looks need provider setup and client permission.',
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
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.info_outline_rounded),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  capabilities['generative_available'] == true
                                      ? 'Generative AI requires an eligible salon plan'
                                      : 'Generative AI is not configured',
                                  style: const TextStyle(fontWeight: FontWeight.w700),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  capabilities['generative_available'] == true
                                      ? 'The provider is available, but this salon plan does not include generative edits. Classic mode remains available.'
                                      : 'Classic mode remains available. Generative edits need a protected provider key and may incur usage charges.',
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  if (_selectedFilterFolder == null) ...[
                    const _EditorSectionHeading(
                      step: '04',
                      title: 'Editing tools',
                      subtitle: 'Choose a category below to see its previews and controls.',
                    ),
                    const SizedBox(height: 10),
                    const _FolderInformation(
                      icon: Icons.touch_app_rounded,
                      title: 'Choose a face tool',
                      message: 'Start with Impression, Skin or Makeup. More face tools are listed below and will become available as their image processors are completed.',
                    ),
                  ] else ...[
                    Row(
                      key: _filterToolsAnchorKey,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        IconButton(
                          key: const ValueKey('back-to-filter-folders'),
                          tooltip: 'All filter folders',
                          onPressed: loading
                              ? null
                              : () => setState(() => _selectedFilterFolder = null),
                          icon: const Icon(Icons.arrow_back_rounded),
                        ),
                        const SizedBox(width: 4),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _selectedFilterFolder!,
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                const SizedBox(height: 3),
                                Text(
                                  _faceFilterFolderDescriptions[_selectedFilterFolder!]!,
                                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                                      ),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        _FilterFolderStatus(status: _filterFolderStatus(_selectedFilterFolder!)),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton.icon(
                        key: const ValueKey('save-current-salon-look'),
                        onPressed: loading || savingLookPreset || !_canProcessSelectedFolder()
                            ? null
                            : _saveCurrentLookPreset,
                        icon: const Icon(Icons.bookmark_add_outlined),
                        label: Text(savingLookPreset ? 'Saving…' : 'Save this look'),
                      ),
                    ),
                    const SizedBox(height: 4),
                    if (_selectedFilterFolder == 'Impression') ...[
                      Text(
                        'Photo finishes',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'These tools adjust overall photo color. Impression starts with skin polish, not an extra makeup look.',
                      ),
                      const SizedBox(height: 10),
                      buildOptionRail(
                        railKey: const ValueKey('photo-finishes-grid'),
                        itemCount: PhotoLookService.names.length,
                        itemBuilder: (context, index) {
                          final look = PhotoLookService.names[index];
                          final entitled = availablePhotoFinishes.contains(look);
                          final requiredPlan = look == 'Soft Glam' ? 'Basic' : 'Pro';
                          return _BeautyOptionTile(
                            key: ValueKey('photo-finish-$index'),
                            title: look,
                            description: _photoFinishDescriptions[look]!,
                            icon: _photoFinishIcons[look]!,
                            selected: selectedLook == look,
                            lockedLabel: entitled ? null : requiredPlan.toUpperCase(),
                            onTap: loading
                                ? null
                                : () {
                                    if (!entitled) {
                                      _showPlanRequired(requiredPlan, look);
                                      return;
                                    }
                                    _selectLook(look);
                                  },
                          );
                        },
                      ),
                      const SizedBox(height: 14),
                      Card(
                        key: const ValueKey('manual-photo-adjustments-panel'),
                        child: ExpansionTile(
                          leading: const Icon(Icons.tune_rounded),
                          title: const Text('Manual photo adjustments'),
                          subtitle: const Text(
                            'Fine-tune the final image before the salon watermark is applied.',
                          ),
                          children: [
                            _buildPhotoAdjustmentSlider(
                              keyName: 'photo-adjust-brightness',
                              label: 'Brightness',
                              valueLabel: '${(brightness * 100).round()}%',
                              value: brightness,
                              min: -0.25,
                              max: 0.25,
                              divisions: 20,
                              update: (value) => brightness = value,
                            ),
                            _buildPhotoAdjustmentSlider(
                              keyName: 'photo-adjust-contrast',
                              label: 'Contrast',
                              valueLabel: '${contrast.toStringAsFixed(2)}×',
                              value: contrast,
                              min: 0.5,
                              max: 1.5,
                              divisions: 20,
                              update: (value) => contrast = value,
                            ),
                            _buildPhotoAdjustmentSlider(
                              keyName: 'photo-adjust-saturation',
                              label: 'Saturation',
                              valueLabel: '${saturation.toStringAsFixed(2)}×',
                              value: saturation,
                              min: 0.0,
                              max: 2.0,
                              divisions: 20,
                              update: (value) => saturation = value,
                            ),
                            _buildPhotoAdjustmentSlider(
                              keyName: 'photo-adjust-warmth',
                              label: 'Warmth',
                              valueLabel: '${(warmth * 100).round()}%',
                              value: warmth,
                              min: -0.25,
                              max: 0.25,
                              divisions: 20,
                              update: (value) => warmth = value,
                            ),
                            _buildPhotoAdjustmentSlider(
                              keyName: 'photo-adjust-sharpness',
                              label: 'Sharpness',
                              valueLabel: '${(sharpness * 100).round()}%',
                              value: sharpness,
                              min: 0.0,
                              max: 1.0,
                              divisions: 20,
                              update: (value) => sharpness = value,
                            ),
                            Align(
                              alignment: Alignment.centerRight,
                              child: TextButton.icon(
                                key: const ValueKey('reset-photo-adjustments'),
                                onPressed: loading ? null : _resetPhotoAdjustments,
                                icon: const Icon(Icons.restart_alt_rounded),
                                label: const Text('Reset adjustments'),
                              ),
                            ),
                            const Padding(
                              padding: EdgeInsets.fromLTRB(16, 0, 16, 14),
                              child: Text(
                                'All five adjustments are processed on the server and included in the downloaded, watermarked PNG. They do not require a paid AI image provider.',
                              ),
                            ),
                          ],
                        ),
                      ),
                    ] else if (_selectedFilterFolder == 'Skin') ...[
                      Text(
                        'Skin polish',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        'Skin Polish Only smooths the face without applying lipstick, blush or eye makeup. Adjust its strength below.',
                      ),
                      const SizedBox(height: 10),
                      _BeautyOptionTile(
                        key: const ValueKey('classic-option-skin_only'),
                        title: _makeupStyles['skin_only']!,
                        description: _makeupStyleDescriptions['skin_only']!,
                        icon: _makeupStyleIcons['skin_only']!,
                        selected: selectedMakeupStyle == 'skin_only',
                        lockedLabel: availableMakeupStyles.contains('skin_only')
                            ? null
                            : 'PRO',
                        onTap: loading
                            ? null
                            : () {
                                if (!availableMakeupStyles.contains('skin_only')) {
                                  _showPlanRequired('Pro', _makeupStyles['skin_only']!);
                                  return;
                                }
                                setState(() {
                                  selectedEngine = 'classic';
                                  selectedMakeupStyle = 'skin_only';
                                  externalAiConsentConfirmed = false;
                                  _clearProcessedResult();
                                });
                              },
                      ),
                    ] else if (_selectedFilterFolder == 'Makeup') ...[
                      if (selectedEngine == 'generative') ...[
                        Text(
                          'Makeup looks',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: _generativeLookCategories.keys
                                .where((category) =>
                                    category != 'Hair' && category != 'Skin')
                                .map((category) {
                              return Padding(
                                padding: const EdgeInsets.only(right: 8),
                                child: ChoiceChip(
                                  key: ValueKey('generative-category-$category'),
                                  avatar: Icon(
                                    _categoryIcons[category] ?? Icons.tune_rounded,
                                    size: 17,
                                  ),
                                  label: Text(category),
                                  selected: _selectedGenerativeCategory == category,
                                  onSelected: loading
                                      ? null
                                      : (_) => setState(
                                            () => _selectedGenerativeCategory = category,
                                          ),
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                        const SizedBox(height: 10),
                        Builder(
                          builder: (context) {
                            final categoryLooks =
                                _generativeLookCategories[_selectedGenerativeCategory] ??
                                    _generativeLookCategories['Looks']!;
                            final visibleLooks = categoryLooks
                                .where((key) =>
                                    !_hairLookKeys.contains(key) && key != 'foundation')
                                .toList();
                            return buildOptionRail(
                              railKey: const ValueKey('generative-options-grid'),
                              itemCount: visibleLooks.length,
                              itemBuilder: (context, index) {
                                final lookKey = visibleLooks[index];
                                return _BeautyOptionTile(
                                  key: ValueKey('generative-option-$lookKey'),
                                  title: _generativeLooks[lookKey]!,
                                  description: _generativeLookDescriptions[lookKey]!,
                                  icon: _generativeLookIcons[lookKey]!,
                                  selected: selectedGenerativeLook == lookKey,
                                  onTap: loading
                                      ? null
                                      : () => setState(() {
                                            selectedGenerativeLook = lookKey;
                                            _clearProcessedResult();
                                            externalAiConsentConfirmed = false;
                                          }),
                                );
                              },
                            );
                          },
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
                          'Makeup styles',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            children: _classicStyleCategories.keys.map((category) {
                              return Padding(
                                padding: const EdgeInsets.only(right: 8),
                                child: ChoiceChip(
                                  key: ValueKey('classic-category-$category'),
                                  avatar: Icon(
                                    _categoryIcons[category] ?? Icons.tune_rounded,
                                    size: 17,
                                  ),
                                  label: Text(category),
                                  selected: _selectedClassicCategory == category,
                                  onSelected: loading
                                      ? null
                                      : (_) => setState(
                                            () => _selectedClassicCategory = category,
                                          ),
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                        const SizedBox(height: 10),
                        buildOptionRail(
                          railKey: const ValueKey('classic-options-grid'),
                          itemCount: _classicStyleCategories[_selectedClassicCategory]!.length,
                          itemBuilder: (context, index) {
                            final styleKey =
                                _classicStyleCategories[_selectedClassicCategory]![index];
                            final style = _makeupStyles[styleKey]!;
                            final entitled = availableMakeupStyles.contains(styleKey);
                            final requiredPlan = styleKey == 'soft_glam' ? 'Basic' : 'Pro';
                            return _BeautyOptionTile(
                              key: ValueKey('classic-option-$styleKey'),
                              title: style,
                              description: _makeupStyleDescriptions[styleKey]!,
                              icon: _makeupStyleIcons[styleKey]!,
                              selected: selectedMakeupStyle == styleKey,
                              lockedLabel: entitled ? null : requiredPlan.toUpperCase(),
                              onTap: loading
                                  ? null
                                  : () {
                                      if (!entitled) {
                                        _showPlanRequired(requiredPlan, style);
                                        return;
                                      }
                                      setState(() {
                                        selectedMakeupStyle = styleKey;
                                        _clearProcessedResult();
                                      });
                                    },
                            );
                          },
                        ),
                      ],
                    ] else if (_selectedFilterFolder == 'Hairstyles') ...[
                      if (!generativeAvailable) ...[
                        _FolderInformation(
                          icon: Icons.auto_awesome_outlined,
                          title: loadingCapabilities || loadingSubscription
                              ? 'Checking hairstyle access'
                              : capabilities['generative_available'] != true
                                  ? 'Generative hairstyles are not configured'
                                  : 'Pro plan required',
                          message: loadingCapabilities || loadingSubscription
                              ? 'MakeupArt is checking whether the hairstyle provider and this salon plan are ready.'
                              : capabilities['generative_available'] != true
                                  ? 'The current Classic engine cannot create new hairstyles. The Generative AI provider must be configured and verified first.'
                                  : 'Hairstyle previews use the external Generative AI provider and require an active Pro-or-higher entitlement. Classic AI cannot create new hairstyles.',
                        ),
                      ] else ...[
                        Text(
                          'Hairstyle previews',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        buildOptionRail(
                          railKey: const ValueKey('hairstyles-options-grid'),
                          itemCount: _generativeLookCategories['Hair']!.length,
                          itemBuilder: (context, index) {
                            final lookKey = _generativeLookCategories['Hair']![index];
                            return _BeautyOptionTile(
                              key: ValueKey('hairstyle-option-$lookKey'),
                              title: _generativeLooks[lookKey]!,
                              description: _generativeLookDescriptions[lookKey]!,
                              icon: _generativeLookIcons[lookKey]!,
                              selected: selectedGenerativeLook == lookKey,
                              onTap: loading
                                  ? null
                                  : () => setState(() {
                                        selectedEngine = 'generative';
                                        selectedGenerativeLook = lookKey;
                                        externalAiConsentConfirmed = false;
                                        _clearProcessedResult();
                                      }),
                            );
                          },
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
                      ],
                    ] else if (_faceEditOptions.containsKey(_selectedFilterFolder)) ...[
                      Text(
                        'Choose a ${_selectedFilterFolder!.toLowerCase()} effect',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      buildOptionRail(
                        railKey: ValueKey('face-edit-options-${_selectedFilterFolder!}'),
                        itemCount: _faceEditOptions[_selectedFilterFolder!]!.length,
                        itemBuilder: (context, index) {
                          final edit = _faceEditOptions[_selectedFilterFolder!]![index];
                          return _BeautyOptionTile(
                            key: ValueKey('face-edit-option-$edit'),
                            title: _faceEditNames[edit]!,
                            description: _faceEditDescriptions[edit]!,
                            icon: _faceEditIcons[edit]!,
                            selected: selectedFaceEffect == edit,
                            onTap: loading
                                ? null
                                : () => setState(() {
                                      selectedFaceEffect = edit;
                                      selectedEngine = 'classic';
                                      _clearProcessedResult();
                                    }),
                          );
                        },
                      ),
                      if (_selectedFilterFolder == 'Age' ||
                          _selectedFilterFolder == 'Gender' ||
                          _selectedFilterFolder == 'Hair Colors') ...[
                        const SizedBox(height: 8),
                        Text(
                          _selectedFilterFolder == 'Age'
                              ? 'These are local cosmetic age-style effects, not a generative age transformation.'
                              : _selectedFilterFolder == 'Gender'
                                  ? 'These are presentation styles only; they do not determine or change a person’s gender identity.'
                                  : 'Hair color is a local preview. Results depend on visible hair and lighting.',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                        ),
                      ],
                    ] else ...[
                      _FolderInformation(
                        icon: _faceFilterFolderIcons[_selectedFilterFolder!]!,
                        title: 'Coming soon',
                        message:
                            'This folder is in the filter roadmap, but its image-processing effect is not implemented yet. It will not change the photo until a real processor is connected and tested.',
                      ),
                    ],
                  ],
                  if (!availablePhotoFinishes.contains(selectedLook)) ...[
                    const SizedBox(height: 8),
                    _FolderInformation(
                      icon: Icons.workspace_premium_outlined,
                      title: 'Photo finish requires a higher plan',
                      message:
                          '$selectedLook is not included in this salon plan. Choose an included finish in Impression or upgrade the salon plan before processing.',
                    ),
                  ],
                  if (selectedFolderToolsAvailable) ...[
                    const SizedBox(height: 6),
                    const _EditorSectionHeading(
                      step: '05',
                      title: 'Fine-tune and process',
                      subtitle: 'Set the strength, confirm permission, then create the result.',
                    ),
                    const SizedBox(height: 10),
                    Text(
                      '${selectedEngine == 'generative'
                          ? 'Generative treatment strength'
                          : (_faceEditOptions.containsKey(_selectedFilterFolder)
                              ? 'Face effect strength'
                              : (_selectedFilterFolder == 'Makeup'
                                  ? 'Skin polish & makeup strength'
                                  : 'Skin polish strength'))} ${(intensity * 100).round()}%',
                    ),
                    Slider(
                      value: intensity,
                      onChanged: loading
                          ? null
                          : (value) => setState(() {
                                if (value == intensity) return;
                                intensity = value;
                                // A processed image belongs to the previous intensity.
                                // Never leave an old result visible as if it used this value.
                                _clearProcessedResult();
                              }),
                    ),
                    const SizedBox(height: 8),
                  ],
                  if (selectedFolderToolsAvailable) ...[
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
                      label: Text(
                        loading
                            ? 'Processing...'
                            : selectedEngine == 'generative'
                                ? 'Generate look'
                                : 'Apply look',
                      ),
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
                      'Your latest 10 edited photos, ready to reopen.',
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
                  Container(
                    key: const ValueKey('saved-salon-looks-panel'),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const _EditorSectionHeading(
                          step: '02',
                          title: 'Saved salon looks',
                          subtitle: 'Tap a saved look to reuse its settings.',
                        ),
                        const SizedBox(height: 12),
                        if (loadingSavedLookPresets)
                          Text(
                            'Loading saved looks…',
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                                ),
                          )
                        else if (savedLookPresets.isEmpty)
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.bookmark_outline_rounded,
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                              const SizedBox(width: 10),
                              const Expanded(
                                child: Text(
                                  'No saved looks yet. Build a look below and tap “Save this look” to reuse its settings.',
                                ),
                              ),
                            ],
                          )
                        else
                          SizedBox(
                            height: 52,
                            child: ListView.separated(
                              scrollDirection: Axis.horizontal,
                              itemCount: savedLookPresets.length,
                              separatorBuilder: (_, __) => const SizedBox(width: 8),
                              itemBuilder: (context, index) {
                                final preset = savedLookPresets[index];
                                return InputChip(
                                  key: ValueKey('salon-look-preset-${preset.id}'),
                                  avatar: const Icon(Icons.bookmark_rounded, size: 17),
                                  label: Text(
                                    '${preset.name} · ${(preset.intensity * 100).round()}%',
                                  ),
                                  onPressed: loading || savingLookPreset
                                      ? null
                                      : () => _applyLookPreset(preset),
                                  onDeleted: loading || savingLookPreset
                                      ? null
                                      : () => _confirmDeleteLookPreset(preset),
                                  deleteButtonTooltipMessage: 'Delete ${preset.name}',
                                );
                              },
                            ),
                          ),
                      ],
                    ),
                  ),
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
                      const SizedBox(height: 14),
                      OutlinedButton.icon(
                        key: const ValueKey('compare-with-faceapp-button'),
                        onPressed: loadingFaceAppComparison || loading
                            ? null
                            : _chooseFaceAppComparison,
                        icon: loadingFaceAppComparison
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.compare_rounded),
                        label: const Text('Linganisha na FaceApp'),
                      ),
                      if (faceAppComparisonBytes != null) ...[
                        const SizedBox(height: 12),
                        Card(
                          key: const ValueKey('faceapp-comparison-panel'),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(
                                  'MAKEUPART VS FACEAPP',
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(
                                        fontWeight: FontWeight.w900,
                                        letterSpacing: 1.1,
                                        color: Theme.of(context).colorScheme.primary,
                                      ),
                                ),
                                const SizedBox(height: 6),
                                const Text(
                                  'Buruta mstari katikati kuona tofauti. Hifadhi kwanza matokeo ya FaceApp kwenye Gallery.',
                                ),
                                const SizedBox(height: 12),
                                BeforeAfterComparison(
                                  key: const ValueKey('makeupart-faceapp-slider'),
                                  height: 260,
                                  beforeLabel: 'MAKEUPART',
                                  afterLabel: 'FACEAPP',
                                  before: Image.memory(
                                    displayedAfterBytes!,
                                    fit: BoxFit.contain,
                                    errorBuilder: (_, __, ___) => const Center(
                                      child: Icon(Icons.broken_image_outlined),
                                    ),
                                  ),
                                  after: Image.memory(
                                    faceAppComparisonBytes!,
                                    fit: BoxFit.contain,
                                    errorBuilder: (_, __, ___) => const Center(
                                      child: Icon(Icons.broken_image_outlined),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                TextButton.icon(
                                  onPressed: loadingFaceAppComparison
                                      ? null
                                      : _chooseFaceAppComparison,
                                  icon: const Icon(Icons.photo_library_outlined),
                                  label: const Text('Badilisha picha ya FaceApp'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ],
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 22),
          DeveloperBranding(
            compact: true,
            centered: true,
            onTap: widget.onAdminPortalAuthenticated == null ? null : _openMrAiDashboard,
          ),
          const SizedBox(height: 16),
        ],
      ),
      bottomNavigationBar: _buildFaceEditorToolbar(),
    );
  }
}

class _EditorSectionHeading extends StatelessWidget {
  const _EditorSectionHeading({
    required this.step,
    required this.title,
    required this.subtitle,
  });

  final String step;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: colors.primaryContainer,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            step,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: colors.onPrimaryContainer,
                  fontWeight: FontWeight.w800,
                ),
          ),
        ),
        const SizedBox(width: 11),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: colors.onSurfaceVariant,
                      height: 1.35,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _FilterFolderStatus extends StatelessWidget {
  const _FilterFolderStatus({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final highlight = status == 'AVAILABLE' || status == 'GENERATIVE AI';
    final planGate = status == 'PRO REQUIRED';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
      decoration: BoxDecoration(
        color: highlight
            ? colors.primaryContainer
            : planGate
                ? colors.tertiaryContainer
                : colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(7),
      ),
      child: Text(
        status,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: highlight
              ? colors.onPrimaryContainer
              : planGate
                  ? colors.onTertiaryContainer
                  : colors.onSurfaceVariant,
          fontSize: 8,
          fontWeight: FontWeight.w800,
          letterSpacing: .25,
        ),
      ),
    );
  }
}


class _FaceEditorToolItem extends StatelessWidget {
  const _FaceEditorToolItem({
    super.key,
    required this.title,
    required this.icon,
    required this.selected,
    required this.ready,
    required this.statusLabel,
    required this.onTap,
  });

  final String title;
  final IconData icon;
  final bool selected;
  final bool ready;
  final String statusLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return SizedBox(
      width: 84,
      child: Semantics(
        button: true,
        selected: selected,
        enabled: onTap != null,
        label: '$title filter preview${statusLabel.isEmpty ? '' : ', $statusLabel'}',
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onTap,
            borderRadius: BorderRadius.circular(13),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 160),
                    width: 74,
                    height: 58,
                    padding: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: selected
                          ? colors.primaryContainer
                          : colors.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected ? colors.primary : Colors.transparent,
                        width: selected ? 1.5 : 0.8,
                      ),
                    ),
                    child: Opacity(
                      opacity: ready ? 1 : .78,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(9),
                        child: Stack(
                          fit: StackFit.expand,
                          children: [
                            FaceSampleArtwork(label: title, height: 48),
                            Positioned(
                              left: 3,
                              bottom: 3,
                              child: Container(
                                width: 18,
                                height: 18,
                                alignment: Alignment.center,
                                decoration: BoxDecoration(
                                  color: Colors.black.withValues(alpha: .62),
                                  shape: BoxShape.circle,
                                ),
                                child: Icon(icon, size: 11, color: Colors.white),
                              ),
                            ),
                            if (statusLabel.isNotEmpty)
                              Positioned(
                                top: 3,
                                right: 3,
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 4,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.black.withValues(alpha: .72),
                                    borderRadius: BorderRadius.circular(5),
                                  ),
                                  child: Text(
                                    statusLabel,
                                    style: const TextStyle(
                                      color: Colors.white,
                                      fontSize: 6.5,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: .2,
                                    ),
                                  ),
                                ),
                              ),
                            if (selected)
                              Positioned(
                                right: 3,
                                bottom: 3,
                                child: Container(
                                  width: 17,
                                  height: 17,
                                  alignment: Alignment.center,
                                  decoration: BoxDecoration(
                                    color: colors.primary,
                                    shape: BoxShape.circle,
                                    border: Border.all(
                                      color: Colors.white,
                                      width: .8,
                                    ),
                                  ),
                                  child: Icon(
                                    Icons.check_rounded,
                                    size: 11,
                                    color: colors.onPrimary,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 9.5,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                      color: selected ? colors.primary : colors.onSurface,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _FolderInformation extends StatelessWidget {
  const _FolderInformation({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Card(
      color: colors.surfaceContainerLow,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 30, color: colors.primary),
            const SizedBox(height: 10),
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 6),
            Text(message),
          ],
        ),
      ),
    );
  }
}

class _BeautyOptionTile extends StatelessWidget {
  const _BeautyOptionTile({
    super.key,
    required this.title,
    required this.description,
    required this.icon,
    required this.selected,
    required this.onTap,
    this.lockedLabel,
  });

  final String title;
  final String description;
  final IconData icon;
  final bool selected;
  final String? lockedLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final locked = lockedLabel != null;

    return Semantics(
      button: true,
      enabled: onTap != null,
      selected: selected,
      label: '$title. $description${locked ? '. Requires $lockedLabel plan.' : ''}',
      child: Material(
        color: selected
            ? colors.secondaryContainer.withValues(alpha: .48)
            : colors.surfaceContainerLow,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: selected ? colors.primary : colors.outlineVariant,
                width: selected ? 1.6 : 0.8,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  height: 76,
                  width: double.infinity,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      FaceSampleArtwork(
                        label: title,
                        height: 76,
                      ),
                      Positioned(
                        left: 5,
                        bottom: 5,
                        child: Container(
                          width: 27,
                          height: 27,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: .94),
                            shape: BoxShape.circle,
                          ),
                          child: Icon(icon, size: 15, color: colors.primary),
                        ),
                      ),
                      if (locked)
                        Positioned(
                          top: 5,
                          right: 5,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: colors.tertiaryContainer,
                              borderRadius: BorderRadius.circular(7),
                            ),
                            child: Text(
                              lockedLabel!,
                              style: TextStyle(
                                color: colors.onTertiaryContainer,
                                fontSize: 8,
                                fontWeight: FontWeight.w900,
                                letterSpacing: .25,
                              ),
                            ),
                          ),
                        )
                      else if (selected)
                        Positioned(
                          top: 5,
                          right: 5,
                          child: Container(
                            width: 24,
                            height: 24,
                            alignment: Alignment.center,
                            decoration: BoxDecoration(
                              color: colors.primary,
                              shape: BoxShape.circle,
                            ),
                            child: Icon(
                              Icons.check_rounded,
                              size: 16,
                              color: colors.onPrimary,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 1),
                Text(
                  description,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                        fontSize: 10.5,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
