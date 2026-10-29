import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/main.dart';
import 'package:makeup_art_v8/pages/beauty_page.dart';
import 'package:makeup_art_v8/pages/login_page.dart';
import 'package:makeup_art_v8/pages/register_page.dart';
import 'package:makeup_art_v8/services/api_client.dart';

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
    tester.view.physicalSize = const Size(800, 1800);
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

    final consentTile = find.byType(CheckboxListTile);
    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);

    await tester.scrollUntilVisible(
      consentTile,
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.ensureVisible(consentTile);
    await tester.pumpAndSettle();
    await tester.tap(consentTile);
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(consentTile).value, isTrue);

    final customerDropdown = find.byType(DropdownButtonFormField<String>);
    await tester.scrollUntilVisible(
      customerDropdown,
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(customerDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    await tester.pumpAndSettle();

    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);
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

    final foldersGrid = find.byKey(const ValueKey('face-filter-folders-grid'));
    await tester.scrollUntilVisible(
      foldersGrid,
      300,
      scrollable: find.byType(Scrollable).first,
    );

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
    expect(find.text('Glasses'), findsOneWidget);

    final impressionFolder = find.byKey(const ValueKey('filter-folder-Impression'));
    await tester.ensureVisible(impressionFolder);
    await tester.pumpAndSettle();
    await tester.tap(impressionFolder);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('photo-finishes-grid')), findsOneWidget);
    expect(find.byKey(const ValueKey('photo-finish-0')), findsOneWidget);
    expect(find.textContaining('Skin polish strength'), findsOneWidget);

    final back = find.byKey(const ValueKey('back-to-filter-folders'));
    await tester.ensureVisible(back);
    await tester.pumpAndSettle();
    await tester.tap(back);
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.byKey(const ValueKey('filter-folder-Makeup')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('filter-folder-Makeup')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('classic-options-grid')), findsOneWidget);
    final eyesCategory = find.byKey(const ValueKey('classic-category-Eyes'));
    await tester.ensureVisible(eyesCategory);
    await tester.pumpAndSettle();
    await tester.tap(eyesCategory);
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('classic-option-smokey_eye')), findsOneWidget);
    expect(find.text('Smokey Eye'), findsOneWidget);
    expect(find.text('Natural'), findsNothing);

    await tester.ensureVisible(back);
    await tester.pumpAndSettle();
    await tester.tap(back);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const ValueKey('filter-folder-Skin')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('filter-folder-Skin')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('classic-option-skin_only')), findsOneWidget);
    expect(find.text('Skin Polish Only'), findsOneWidget);

    await tester.ensureVisible(back);
    await tester.pumpAndSettle();
    await tester.tap(back);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const ValueKey('filter-folder-Sizes')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('filter-folder-Sizes')));
    await tester.pumpAndSettle();

    expect(find.text('Coming soon'), findsOneWidget);
    expect(
      find.textContaining('image-processing effect is not implemented yet'),
      findsOneWidget,
    );
  });

}
