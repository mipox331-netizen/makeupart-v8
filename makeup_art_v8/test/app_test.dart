import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/main.dart';
import 'package:makeup_art_v8/pages/beauty_page.dart';
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

class _ConsentTestApi extends ApiClient {
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

void main() {
  testWidgets('MakeupArt V8 app boots', (tester) async {
    await tester.pumpWidget(const MakeupArtApp());
    await tester.pump();
    expect(find.byType(MakeupArtApp), findsOneWidget);
  });

  testWidgets('registration explains when email already exists', (tester) async {
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

    await tester.ensureVisible(consentTile);
    await tester.tap(consentTile);
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(consentTile).value, isTrue);

    final customerDropdown = find.byType(DropdownButtonFormField<String>);
    await tester.ensureVisible(customerDropdown);
    await tester.tap(customerDropdown);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    await tester.pumpAndSettle();

    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);
    expect(find.text('AI consent is active'), findsOneWidget);
  });

}
