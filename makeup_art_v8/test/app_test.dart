import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/main.dart';

void main() {
  testWidgets('MakeupArt V8 app boots', (tester) async {
    await tester.pumpWidget(const MakeupArtApp());
    await tester.pump();
    expect(find.byType(MakeupArtApp), findsOneWidget);
  });
}
