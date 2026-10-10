import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/main.dart';
import 'package:makeup_art_v8/pages/beauty_page.dart';
import 'package:makeup_art_v8/services/api_client.dart';

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

void main() {
  testWidgets('MakeupArt V8 app boots', (tester) async {
    await tester.pumpWidget(const MakeupArtApp());
    await tester.pump();
    expect(find.byType(MakeupArtApp), findsOneWidget);
  });

  testWidgets('switching clients clears prior photo consent confirmation', (tester) async {
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

    await tester.tap(consentTile);
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(consentTile).value, isTrue);

    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Alice One').last);
    await tester.pumpAndSettle();

    expect(tester.widget<CheckboxListTile>(consentTile).value, isFalse);
    expect(find.text('AI consent is active'), findsOneWidget);
  });
}
