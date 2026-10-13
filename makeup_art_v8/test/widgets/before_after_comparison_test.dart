import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/widgets/before_after_comparison.dart';

void main() {
  testWidgets('shows original and finished labels with a draggable divider',
      (tester) async {
    tester.view.physicalSize = const Size(800, 500);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Padding(
            padding: EdgeInsets.all(16),
            child: BeforeAfterComparison(
              height: 320,
              before: ColoredBox(color: Colors.red),
              after: ColoredBox(color: Colors.blue),
            ),
          ),
        ),
      ),
    );

    expect(find.text('BEFORE'), findsOneWidget);
    expect(find.text('AFTER'), findsOneWidget);
    expect(find.byKey(const ValueKey('before-after-handle')), findsOneWidget);

    await tester.drag(
      find.byKey(const ValueKey('before-after-handle')),
      const Offset(100, 0),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
  });
}
