import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:makeup_art_v8/pages/login_page.dart';
import 'package:makeup_art_v8/pages/register_page.dart';
import 'package:makeup_art_v8/services/api_client.dart';

TextField _passwordField(WidgetTester tester) {
  return tester.widget<TextField>(
    find.byWidgetPredicate(
      (widget) => widget is TextField && widget.decoration?.labelText == 'Password',
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('login password can be shown and hidden', (tester) async {
    tester.view.physicalSize = const Size(400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(home: LoginPage(api: ApiClient(), onLoggedIn: () {})),
    );

    expect(_passwordField(tester).obscureText, isTrue);
    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();
    expect(_passwordField(tester).obscureText, isFalse);

    await tester.tap(find.byTooltip('Hide password'));
    await tester.pump();
    expect(_passwordField(tester).obscureText, isTrue);
  });

  testWidgets('registration password can be shown and hidden', (tester) async {
    tester.view.physicalSize = const Size(400, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(home: RegisterPage(api: ApiClient(), onRegistered: () {})),
    );

    expect(_passwordField(tester).obscureText, isTrue);
    await tester.tap(find.byTooltip('Show password'));
    await tester.pump();
    expect(_passwordField(tester).obscureText, isFalse);

    await tester.tap(find.byTooltip('Hide password'));
    await tester.pump();
    expect(_passwordField(tester).obscureText, isTrue);
  });
}
