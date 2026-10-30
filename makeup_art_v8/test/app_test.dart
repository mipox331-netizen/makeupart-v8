import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/main.dart';
import 'package:makeup_art_v8/pages/beauty_page.dart';
import 'package:makeup_art_v8/pages/login_page.dart';
import 'package:makeup_art_v8/pages/register_page.dart';
import 'package:makeup_art_v8/services/api_client.dart';
import 'package:makeup_art_v8/services/salon_look_preset_store.dart';
import 'package:makeup_art_v8/widgets/face_sample_artwork.dart';

class _FakeRegistrationApi extends ApiClient {
  _FakeRegistrationApi({this.registerFailure, this.loginFailure});

  final Object? registerFailure;
  final Object? loginFailure;
  bool registerCalled = false;

  @override
  Future<void> register({
    required String salonName,
    required String ownerFullName,
    required String email,
    required String password,
    String? phone,
  }) async {
    registerCalled = true;
    if (registerFailure != null) throw registerFailure!;
  }

  @override
  Future<void> login(String email, String password) async {
    if (loginFailure != null) throw loginFailure!;
  }
}

class _ExpiredSessionApi extends ApiClient {
  bool tokensCleared = false;

  @override
  Future<Map<String, dynamic>> currentUser() async {
    final request = RequestOptions(path: '/auth/me');
    throw DioException(
      requestOptions: request,
      response: Response(
        requestOptions: request,
        statusCode: 401,
        data: {'detail': 'Could not validate credentials'},
      ),
    );
  }

  @override
  Future<void> logoutLocal() async {
    tokensCleared = true;
  }
}

class _FakeLoginApi extends ApiClient {
  _FakeLoginApi(this.failure);

  final Object failure;

  @override
  Future<void> login(String email, String password) async {
    throw failure;
  }
}

class _ConsentTestApi extends ApiClient {
  @override
  Future<Map<String, dynamic>> getSubscription() async => {
        'plan': 'free',
        'available_makeup_styles': ['natural', 'skin_only'],
        'available_photo_finishes': ['Natural Finish', 'Warm Glow'],
        'generative_engine_entitled': false,
      };

  @override
  Future<Map<String, dynamic>> getBeautyCapabilities() async => {
        'classic_available': true,
        'generative_available': false,
        'third_party_processing_requires_consent': true,
      };

  @override
  Future<List<Map<String, dynamic>>> listCustomers() async => [
        {'id': 'customer-a', 'first_name': 'Alice', 'last_name': 'One'},
        {'id': 'customer-b', 'first_name': 'Bob', 'last_name': 'Two'},
      ];

  @override
  Future<Map<String, dynamic>?> getActiveConsent(String customerId) async =>
      {'id': 'stored-consent', 'customer_id': customerId};
}


class _InMemorySalonLookPresetStore extends SalonLookPresetStore {
  _InMemorySalonLookPresetStore({
    required super.scope,
    Iterable<SalonLookPreset> initial = const [],
  }) : _items = initial.toList();

  final List<SalonLookPreset> _items;
  int _nextId = 0;

  @override
  Future<List<SalonLookPreset>> list() async =>
      List<SalonLookPreset>.unmodifiable(_items);

  @override
  Future<SalonLookPreset> save({
    required String name,
    required String folder,
    required String engine,
    required String makeupStyle,
    required String generativeLook,
    required String photoFinish,
    required double intensity,
  }) async {
    final cleanName = name.trim();
    final existingIndex = _items.indexWhere(
      (item) => item.name.toLowerCase() == cleanName.toLowerCase(),
    );
    if (existingIndex < 0 && _items.length >= SalonLookPresetStore.maxPresets) {
      throw const SalonLookPresetLimitException(SalonLookPresetStore.maxPresets);
    }
    final existing = existingIndex < 0 ? null : _items[existingIndex];
    final preset = SalonLookPreset(
      id: existing?.id ?? 'memory-${_nextId++}',
      name: cleanName,
      folder: folder,
      engine: engine,
      makeupStyle: makeupStyle,
      generativeLook: generativeLook,
      photoFinish: photoFinish,
      intensity: intensity,
      updatedAt: DateTime.now().toUtc(),
    );
    if (existingIndex < 0) {
      _items.add(preset);
    } else {
      _items[existingIndex] = preset;
    }
    return preset;
  }

  @override
  Future<void> delete(String id) async {
    _items.removeWhere((item) => item.id == id);
  }
}

class _ConsentRaceApi extends _ConsentTestApi {
  final firstClientLookup = Completer<void>();

  @override
  Future<Map<String, dynamic>?> getActiveConsent(String customerId) async {
    if (customerId == 'customer-a') {
      await firstClientLookup.future;
      throw Exception('simulated stale consent request failure');
    }
    return {'id': 'stored-consent', 'customer_id': customerId};
  }
}

class _ConsentToggleApi extends _ConsentTestApi {
  final consentWriteCompleted = Completer<void>();
  int consentWriteCalls = 0;
  bool consentGranted = true;

  @override
  Future<Map<String, dynamic>?> getActiveConsent(String customerId) async =>
      consentGranted ? {'id': 'stored-consent', 'customer_id': customerId} : null;

  @override
  Future<void> setCustomerConsent({
    required String customerId,
    required bool granted,
  }) async {
    consentWriteCalls++;
    await consentWriteCompleted.future;
    consentGranted = granted;
  }
}

DioException _responseError(int status, Object data) {
  final request = RequestOptions(path: '/auth/register');
  return DioException(
    requestOptions: request,
    response: Response(
      requestOptions: request,
      statusCode: status,
      data: data,
    ),
  );
}

Future<void> _fillForm(WidgetTester tester) async {
  await tester.enterText(find.byType(TextField).at(0), 'Test Salon');
  await tester.enterText(find.byType(TextField).at(1), 'Test Owner');
  await tester.enterText(find.byType(TextField).at(2), 'owner@example.com');
  await tester.enterText(find.byType(TextField).at(4), 'SafePassword123');
}

void _useTallViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

// The editor intentionally contains an indeterminate capability indicator and
// the save dialog has an autofocus text field. pumpAndSettle waits forever for
// those repeating animations; advance only the finite UI transitions under test.
Future<void> _pumpEditor(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

Future<void> _pumpUntilFound(WidgetTester tester, Finder finder) async {
  for (var attempt = 0; attempt < 30; attempt++) {
    if (finder.evaluate().isNotEmpty) return;
    await tester.pump(const Duration(milliseconds: 100));
  }
  expect(finder, findsOneWidget);
}

void main() {
  testWidgets('MakeupArt V8 identifies MOOG 343 as creator', (tester) async {
    await tester.pumpWidget(const MakeupArtApp());
    await tester.pump();
    expect(find.byType(MakeupArtApp), findsOneWidget);
    expect(find.text('MakeupArt V8'), findsOneWidget);
    expect(find.text('MOOG 343'), findsOneWidget);
    expect(find.text('Imetengenezwa na'), findsOneWidget);
  });

  testWidgets('expired session returns to sign-in instead of a stuck error', (tester) async {
    _useTallViewport(tester);
    final api = _ExpiredSessionApi();
    var logoutRequested = false;

    await tester.pumpWidget(
      MaterialApp(
        home: SessionGate(
          api: api,
          onLogout: () => logoutRequested = true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(api.tokensCleared, isTrue);
    expect(logoutRequested, isTrue);
    expect(find.textContaining('Could not load account status:'), findsNothing);
  });

  testWidgets('login server error includes a safe support reference', (tester) async {
    _useTallViewport(tester);
    final api = _FakeLoginApi(
      _responseError(500, {
        'detail': 'Internal server error',
        'request_id': 'login-trace-123',
      }),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: LoginPage(api: api, onLoggedIn: () {}),
      ),
    );
    await tester.enterText(find.byType(TextField).at(0), 'owner@example.com');
    await tester.enterText(find.byType(TextField).at(1), 'SafePassword123');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Support reference: login-trace-123'), findsOneWidget);
  });

  testWidgets('registration server error includes a safe support reference', (tester) async {
    _useTallViewport(tester);
    final api = _FakeRegistrationApi(
      registerFailure: _responseError(500, {
        'detail': 'Internal server error',
        'request_id': 'register-trace-123',
      }),
    );
    await tester.pumpWidget(
      MaterialApp(home: RegisterPage(api: api, onRegistered: () {})),
    );
    await _fillForm(tester);
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(find.textContaining('Support reference: register-trace-123'), findsOneWidget);
  });

  testWidgets('registration explains when email already exists', (tester) async {
    _useTallViewport(tester);
    final api = _FakeRegistrationApi(
      registerFailure: _responseError(409, {'detail': 'Email already registered'}),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: RegisterPage(api: api, onRegistered: () {}),
      ),
    );
    await _fillForm(tester);
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(find.textContaining('already has an account'), findsOneWidget);
    expect(find.text('Back to sign in'), findsOneWidget);
    expect(api.registerCalled, isTrue);
  });

  testWidgets('registration success but login failure is not reported as registration failure', (tester) async {
    _useTallViewport(tester);
    final api = _FakeRegistrationApi(loginFailure: StateError('temporary sign-in failure'));
    var didAuthenticate = false;
    await tester.pumpWidget(
      MaterialApp(
        home: RegisterPage(
          api: api,
          onRegistered: () => didAuthenticate = true,
        ),
      ),
    );
    await _fillForm(tester);
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();

    expect(api.registerCalled, isTrue);
    expect(find.textContaining('account was created successfully'), findsOneWidget);
    expect(find.text('Back to sign in'), findsWidgets);
    expect(didAuthenticate, isFalse);
  });
  testWidgets('switching clients clears the previous consent confirmation', (tester) async {
    _useTallViewport(tester);
    // The redesigned studio adds a hero and history area before the controls.
    // Keep this behavior test focused on consent state, not viewport scrolling.
    tester.view.physicalSize = const Size(800, 3200);
    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: _ConsentTestApi(),
          onLogout: () {},
          salonId: 'salon-a',
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Consent is presented only after entering a folder that has a real processor.
    final makeupFolder = find.byKey(const ValueKey('filter-folder-Makeup'));
    await tester.ensureVisible(makeupFolder);
    await tester.pumpAndSettle();
    await tester.tap(makeupFolder);
    await tester.pumpAndSettle();

    final consentTile = find.byType(CheckboxListTile);
    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);

    await tester.ensureVisible(consentTile);
    await tester.pumpAndSettle();
    await tester.tap(consentTile);
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(consentTile).value, isTrue);

    final customerDropdown = find.byType(DropdownButtonFormField<String>);
    await tester.ensureVisible(customerDropdown);
    await tester.pumpAndSettle();
    await tester.tap(customerDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    await tester.pumpAndSettle();

    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);
    expect(find.text('AI consent is active'), findsOneWidget);
  });


  testWidgets('stored consent cannot be toggled twice while a request is pending', (tester) async {
    _useTallViewport(tester);
    tester.view.physicalSize = const Size(800, 3200);
    final api = _ConsentToggleApi();

    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: api,
          onLogout: () {},
          salonId: 'consent-toggle-test',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final dropdown = find.byType(DropdownButtonFormField<String>);
    await tester.ensureVisible(dropdown);
    await tester.tap(dropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    await tester.pumpAndSettle();
    expect(find.text('AI consent is active'), findsOneWidget);

    final revokeButton = find.widgetWithText(TextButton, 'Revoke');
    await tester.ensureVisible(revokeButton);
    await tester.tap(revokeButton);
    await tester.pump();

    expect(api.consentWriteCalls, 1);
    final savingButton = find.widgetWithText(TextButton, 'Saving...');
    expect(savingButton, findsOneWidget);
    expect(tester.widget<TextButton>(savingButton).onPressed, isNull);

    api.consentWriteCompleted.complete();
    await tester.pumpAndSettle();

    expect(api.consentWriteCalls, 1);
    expect(api.consentGranted, isFalse);
    expect(find.text('AI consent is not active'), findsOneWidget);
  });

  testWidgets('a late consent failure for the previous client cannot revoke the current client', (tester) async {
    _useTallViewport(tester);
    tester.view.physicalSize = const Size(800, 3200);
    final api = _ConsentRaceApi();

    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: api,
          onLogout: () {},
          salonId: 'consent-race-test',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final dropdown = find.byType(DropdownButtonFormField<String>);
    await tester.tap(dropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    // The intentionally pending consent request can keep unrelated UI
    // animations alive. Advance the dropdown transition without settling it.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    // Alice's consent lookup is still pending. Select Bob before it fails.
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Bob Two').last);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.text('AI consent is active'), findsOneWidget);

    api.firstClientLookup.complete();
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.text('AI consent is active'), findsOneWidget);
  });

  testWidgets('Face filter folders route to real tools and label unfinished categories', (tester) async {
    _useTallViewport(tester);
    tester.view.physicalSize = const Size(800, 1800);

    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: _ConsentTestApi(),
          onLogout: () {},
          salonId: 'salon-editor-test',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final foldersToolbar = find.byKey(const ValueKey('face-filter-folders-grid'));
    expect(foldersToolbar, findsOneWidget);

    expect(find.byKey(const ValueKey('saved-salon-looks-panel')), findsOneWidget);
    expect(find.text('Editing tools'), findsOneWidget);
    expect(find.text('Ready to use'), findsNothing);
    expect(find.text('More filters in development'), findsNothing);
    expect(find.text('Impression'), findsOneWidget);
    expect(find.text('Skin'), findsOneWidget);
    expect(find.text('Sizes'), findsOneWidget);
    expect(find.text('Hairstyles'), findsOneWidget);
    expect(find.text('Hair Colors'), findsOneWidget);
    expect(find.text('Smiles'), findsOneWidget);
    expect(find.text('Features'), findsOneWidget);
    expect(find.text('Beards'), findsOneWidget);
    expect(find.text('Makeup'), findsOneWidget);
    expect(find.text('Age'), findsOneWidget);
    expect(find.text('Gender'), findsOneWidget);
    final glassesFolder = find.byKey(const ValueKey('filter-folder-Glasses'));
    // Scroll the actual horizontal ListView until its lazily-built final item
    // exists. Dragging the parent container is not guaranteed to reach the
    // ListView's max extent on every CI viewport/device-pixel configuration.
    final folderScrollView = find.descendant(
      of: foldersToolbar,
      matching: find.byType(Scrollable),
    ).first;
    await tester.scrollUntilVisible(
      glassesFolder,
      160,
      scrollable: folderScrollView,
    );
    await _pumpEditor(tester);
    expect(glassesFolder, findsOneWidget);
    expect(find.text('Glasses'), findsOneWidget);
    await tester.drag(foldersToolbar, const Offset(1000, 0));
    await _pumpEditor(tester);

    final impressionFolder = find.byKey(const ValueKey('filter-folder-Impression'));
    await tester.scrollUntilVisible(
      impressionFolder,
      120,
      scrollable: folderScrollView,
    );
    await _pumpEditor(tester);
    await tester.tap(impressionFolder);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('photo-finishes-grid')), findsOneWidget);
    expect(find.byType(FaceSampleArtwork), findsNWidgets(5));
    expect(find.byKey(const ValueKey('photo-finish-0')), findsOneWidget);
    expect(find.textContaining('Skin polish strength'), findsOneWidget);

    final back = find.byKey(const ValueKey('back-to-filter-folders'));
    await tester.scrollUntilVisible(
      back,
      120,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpEditor(tester);
    await tester.tap(back);
    await tester.pumpAndSettle();

    final makeupFolder = find.byKey(const ValueKey('filter-folder-Makeup'));
    await tester.scrollUntilVisible(
      makeupFolder,
      120,
      scrollable: folderScrollView,
    );
    await _pumpEditor(tester);
    await tester.tap(makeupFolder);
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('classic-options-grid')), findsOneWidget);
    final eyesCategory = find.byKey(const ValueKey('classic-category-Eyes'));
    await tester.scrollUntilVisible(
      eyesCategory,
      120,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpEditor(tester);
    await tester.tap(eyesCategory);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('classic-option-smokey_eye')), findsOneWidget);
    expect(find.text('Smokey Eye'), findsOneWidget);
    expect(find.text('Natural'), findsNothing);

    await tester.scrollUntilVisible(
      back,
      120,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpEditor(tester);
    await tester.tap(back);
    await tester.pumpAndSettle();
    final skinFolder = find.byKey(const ValueKey('filter-folder-Skin'));
    await tester.scrollUntilVisible(
      skinFolder,
      120,
      scrollable: folderScrollView,
    );
    await _pumpEditor(tester);
    await tester.tap(skinFolder);
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('classic-option-skin_only')), findsOneWidget);
    expect(find.text('Skin Polish Only'), findsOneWidget);

    await tester.scrollUntilVisible(
      back,
      120,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpEditor(tester);
    await tester.tap(back);
    await tester.pumpAndSettle();
    final sizesFolder = find.byKey(const ValueKey('filter-folder-Sizes'));
    await tester.scrollUntilVisible(
      sizesFolder,
      120,
      scrollable: folderScrollView,
    );
    await _pumpEditor(tester);
    await tester.tap(sizesFolder);
    await tester.pumpAndSettle();

    expect(find.text('Coming soon'), findsOneWidget);
    expect(
      find.textContaining('image-processing effect is not implemented yet'),
      findsOneWidget,
    );

    final creatorCredit = find.text('MOOG 343');
    await tester.scrollUntilVisible(
      creatorCredit,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    await _pumpEditor(tester);
    expect(creatorCredit, findsOneWidget);
  });


  testWidgets('a saved premium photo finish cannot bypass a free salon plan', (tester) async {
    _useTallViewport(tester);
    final saved = SalonLookPreset(
      id: 'premium-look-1',
      name: 'Studio Gold',
      folder: 'Makeup',
      engine: 'classic',
      makeupStyle: 'natural',
      generativeLook: 'full_glam',
      photoFinish: 'Golden Hour',
      intensity: 0.6,
      updatedAt: DateTime.utc(2026, 10, 30),
    );
    final presetStore = _InMemorySalonLookPresetStore(
      scope: 'free-salon',
      initial: [saved],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: _ConsentTestApi(),
          onLogout: () {},
          salonId: 'free-salon',
          lookPresetStore: presetStore,
        ),
      ),
    );
    await _pumpEditor(tester);

    final presetChip = find.byKey(ValueKey('salon-look-preset-${saved.id}'));
    await _pumpUntilFound(tester, presetChip);
    final savedLooksPanel = find.byKey(const ValueKey('saved-salon-looks-panel'));
    await tester.scrollUntilVisible(
      savedLooksPanel,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    final presetScrollView = find.descendant(
      of: savedLooksPanel,
      matching: find.byType(Scrollable),
    ).first;
    await tester.scrollUntilVisible(
      presetChip,
      120,
      scrollable: presetScrollView,
    );
    await tester.tap(presetChip);
    await _pumpEditor(tester);

    expect(
      find.textContaining('Golden Hour requires the Pro plan or higher'),
      findsOneWidget,
    );
    expect(find.text('Process with AI'), findsNothing);
  });

  testWidgets('salon look presets can be saved and reapplied', (tester) async {
    _useTallViewport(tester);
    final presetStore = _InMemorySalonLookPresetStore(scope: 'widget-salon');

    await tester.pumpWidget(
      MaterialApp(
        home: BeautyPage(
          api: _ConsentTestApi(),
          onLogout: () {},
          salonId: 'widget-salon',
          lookPresetStore: presetStore,
        ),
      ),
    );
    await _pumpEditor(tester);

    final impressionFolder = find.byKey(const ValueKey('filter-folder-Impression'));
    final folderScrollView = find.descendant(
      of: find.byKey(const ValueKey('face-filter-folders-grid')),
      matching: find.byType(Scrollable),
    ).first;
    await tester.scrollUntilVisible(
      impressionFolder,
      120,
      scrollable: folderScrollView,
    );
    await tester.tap(impressionFolder);
    await _pumpEditor(tester);

    final saveButton = find.byKey(const ValueKey('save-current-salon-look'));
    await tester.scrollUntilVisible(
      saveButton,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(saveButton);
    // The name field requests keyboard focus and has a blinking caret. A
    // bounded frame pump avoids waiting forever for that intentional ticker.
    await _pumpEditor(tester);

    final nameField = find.byKey(const ValueKey('salon-look-name-field'));
    expect(nameField, findsOneWidget);
    await tester.enterText(nameField, 'Warm Studio');
    await tester.tap(find.byKey(const ValueKey('save-salon-look-confirm')));
    await _pumpEditor(tester);

    final saved = await presetStore.list();
    expect(saved, hasLength(1));
    expect(saved.single.name, 'Warm Studio');

    final presetChip = find.byKey(
      ValueKey('salon-look-preset-${saved.single.id}'),
    );
    await _pumpUntilFound(tester, presetChip);
    final savedLooksPanel = find.byKey(const ValueKey('saved-salon-looks-panel'));
    await tester.scrollUntilVisible(
      savedLooksPanel,
      160,
      scrollable: find.byType(Scrollable).first,
    );
    final presetScrollView = find.descendant(
      of: savedLooksPanel,
      matching: find.byType(Scrollable),
    ).first;
    await tester.scrollUntilVisible(
      presetChip,
      120,
      scrollable: presetScrollView,
    );
    await tester.tap(presetChip);
    await _pumpEditor(tester);
    expect(find.byKey(const ValueKey('photo-finishes-grid')), findsOneWidget);
  });




}
