import 'dart:math' as math;

import 'package:flutter/material.dart';

/// A lightweight, original illustrated style sample for filter cards.
///
/// This is deliberately artwork rather than a claimed edited photo. The real
/// result is created only after the selected portrait is processed.
class FaceSampleArtwork extends StatelessWidget {
  const FaceSampleArtwork({
    super.key,
    required this.label,
    this.height = 68,
  });

  final String label;
  final double height;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(12);
    return ClipRRect(
      borderRadius: radius,
      child: SizedBox(
        height: height,
        width: double.infinity,
        child: CustomPaint(
          painter: _FaceSamplePainter(label),
        ),
      ),
    );
  }
}

class _FaceSamplePainter extends CustomPainter {
  const _FaceSamplePainter(this.label);

  final String label;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;

    final name = label.toLowerCase();
    final seed = label.runes.fold<int>(0, (sum, rune) => sum + rune);
    const backdrops = <List<Color>>[
      [Color(0xFFF8DCD5), Color(0xFFE5C8EF)],
      [Color(0xFFDDE8F4), Color(0xFFC8DCD8)],
      [Color(0xFFF5E8C9), Color(0xFFEBC5C8)],
      [Color(0xFFE0D9F5), Color(0xFFF1D7C3)],
      [Color(0xFFD4E7E6), Color(0xFFE7D8F0)],
    ];
    const skinTones = <Color>[
      Color(0xFFE9B99B),
      Color(0xFFC98A67),
      Color(0xFF9C6247),
      Color(0xFF75452F),
      Color(0xFFD7A184),
    ];
    final backdrop = backdrops[seed % backdrops.length];
    final skin = skinTones[(seed ~/ 3) % skinTones.length];
    final hair = name.contains('silver')
        ? const Color(0xFFBFC6D2)
        : name.contains('blonde')
            ? const Color(0xFFB98C48)
            : name.contains('copper')
                ? const Color(0xFF9B4F35)
                : name.contains('black')
                    ? const Color(0xFF241D26)
                    : const Color(0xFF38262A);
    final lip = name.contains('natural') || name.contains('skin')
        ? const Color(0xFFB66D72)
        : name.contains('bridal') || name.contains('rose')
            ? const Color(0xFFC85F79)
            : name.contains('smokey') || name.contains('editorial')
                ? const Color(0xFF8D3E59)
                : const Color(0xFFD45A68);
    final glam = name.contains('makeup') ||
        name.contains('glam') ||
        name.contains('lip') ||
        name.contains('blush') ||
        name.contains('smokey') ||
        name.contains('cat eye') ||
        name.contains('bridal') ||
        name.contains('eyeshadow') ||
        name.contains('editorial');

    final bounds = Offset.zero & size;
    canvas.drawRect(
      bounds,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: backdrop,
        ).createShader(bounds),
    );

    final glowPaint = Paint()..color = Colors.white.withValues(alpha: .34);
    canvas.drawCircle(
      Offset(size.width * .12, size.height * .15),
      size.height * .32,
      glowPaint,
    );
    canvas.drawCircle(
      Offset(size.width * .92, size.height * .82),
      size.height * .30,
      glowPaint,
    );

    final cx = size.width * .5;
    final faceWidth = math.min(size.width * .34, size.height * .78).toDouble();
    final faceHeight = size.height * .63;
    final faceTop = size.height * .12;
    final faceRect = Rect.fromLTWH(
      cx - faceWidth / 2,
      faceTop,
      faceWidth,
      faceHeight,
    );
    final neckWidth = faceWidth * .28;
    final neckTop = faceRect.bottom - faceHeight * .05;

    final body = Path()
      ..moveTo(cx - size.width * .34, size.height)
      ..quadraticBezierTo(
        cx - size.width * .31,
        size.height * .70,
        cx - neckWidth * .78,
        neckTop + faceHeight * .43,
      )
      ..lineTo(cx + neckWidth * .78, neckTop + faceHeight * .43)
      ..quadraticBezierTo(
        cx + size.width * .31,
        size.height * .70,
        cx + size.width * .34,
        size.height,
      )
      ..close();
    canvas.drawPath(body, Paint()..color = const Color(0xFF5D526F));
    canvas.drawRRect(
      RRect.fromRectAndRadius(
        Rect.fromCenter(
          center: Offset(cx, neckTop + faceHeight * .20),
          width: neckWidth,
          height: faceHeight * .34,
        ),
        Radius.circular(neckWidth * .28),
      ),
      Paint()..color = skin,
    );

    final hairShape = Path()
      ..moveTo(cx - faceWidth * .52, faceTop + faceHeight * .34)
      ..cubicTo(
        cx - faceWidth * .73,
        faceTop - faceHeight * .04,
        cx - faceWidth * .37,
        faceTop - faceHeight * .16,
        cx,
        faceTop + faceHeight * .015,
      )
      ..cubicTo(
        cx + faceWidth * .36,
        faceTop - faceHeight * .16,
        cx + faceWidth * .73,
        faceTop - faceHeight * .03,
        cx + faceWidth * .52,
        faceTop + faceHeight * .34,
      )
      ..lineTo(cx + faceWidth * .60, faceRect.bottom - faceHeight * .03)
      ..quadraticBezierTo(
        cx + faceWidth * .39,
        faceRect.bottom + faceHeight * .18,
        cx + faceWidth * .29,
        faceRect.bottom - faceHeight * .10,
      )
      ..lineTo(cx - faceWidth * .29, faceRect.bottom - faceHeight * .10)
      ..quadraticBezierTo(
        cx - faceWidth * .39,
        faceRect.bottom + faceHeight * .18,
        cx - faceWidth * .60,
        faceRect.bottom - faceHeight * .03,
      )
      ..close();
    canvas.drawPath(hairShape, Paint()..color = hair);

    final earPaint = Paint()..color = skin;
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx - faceWidth * .49, faceTop + faceHeight * .48),
        width: faceWidth * .17,
        height: faceHeight * .19,
      ),
      earPaint,
    );
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx + faceWidth * .49, faceTop + faceHeight * .48),
        width: faceWidth * .17,
        height: faceHeight * .19,
      ),
      earPaint,
    );
    canvas.drawRRect(
      RRect.fromRectAndRadius(faceRect, Radius.elliptical(faceWidth * .42, faceHeight * .42)),
      Paint()..color = skin,
    );

    final cheekPaint = Paint()
      ..color = (glam ? lip : const Color(0xFFD68B80)).withValues(alpha: glam ? .24 : .12);
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx - faceWidth * .29, faceTop + faceHeight * .61),
        width: faceWidth * .20,
        height: faceHeight * .105,
      ),
      cheekPaint,
    );
    canvas.drawOval(
      Rect.fromCenter(
        center: Offset(cx + faceWidth * .29, faceTop + faceHeight * .61),
        width: faceWidth * .20,
        height: faceHeight * .105,
      ),
      cheekPaint,
    );

    final eyeY = faceTop + faceHeight * .445;
    final eyeWidth = faceWidth * .19;
    final eyeHeight = faceHeight * .075;
    final eyeFill = Paint()..color = const Color(0xFF39272A);
    final whitePaint = Paint()..color = const Color(0xFFFFF7F0);
    final browPaint = Paint()
      ..color = hair
      ..strokeWidth = math.max(1.0, size.height * .022).toDouble()
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    for (final side in const [-1.0, 1.0]) {
      final eyeCenter = Offset(cx + side * faceWidth * .225, eyeY);
      if (glam && (name.contains('smokey') || name.contains('editorial'))) {
        final shadowRect = Rect.fromCenter(
          center: Offset(eyeCenter.dx, eyeCenter.dy - eyeHeight * .42),
          width: eyeWidth * 1.22,
          height: eyeHeight * 1.55,
        );
        canvas.drawOval(
          shadowRect,
          Paint()..color = const Color(0xFF6D4B70).withValues(alpha: .48),
        );
      }
      canvas.drawOval(
        Rect.fromCenter(center: eyeCenter, width: eyeWidth, height: eyeHeight),
        whitePaint,
      );
      canvas.drawCircle(
        Offset(eyeCenter.dx, eyeCenter.dy),
        math.max(1.2, eyeHeight * .36).toDouble(),
        eyeFill,
      );
      final brow = Path()
        ..moveTo(eyeCenter.dx - eyeWidth * .57, eyeY - eyeHeight * 1.18)
        ..quadraticBezierTo(
          eyeCenter.dx,
          eyeY - eyeHeight * 2.15,
          eyeCenter.dx + eyeWidth * .57,
          eyeY - eyeHeight * 1.10,
        );
      canvas.drawPath(brow, browPaint);
      if (name.contains('cat eye')) {
        final wing = Path()
          ..moveTo(eyeCenter.dx + side * eyeWidth * .42, eyeCenter.dy)
          ..lineTo(eyeCenter.dx + side * eyeWidth * .88, eyeCenter.dy - eyeHeight * .62);
        canvas.drawPath(
          wing,
          Paint()
            ..color = const Color(0xFF3A262D)
            ..strokeWidth = math.max(1.0, size.height * .018).toDouble()
            ..strokeCap = StrokeCap.round
            ..style = PaintingStyle.stroke,
        );
      }
    }

    final nose = Path()
      ..moveTo(cx, eyeY + eyeHeight * .35)
      ..quadraticBezierTo(
        cx - faceWidth * .055,
        eyeY + faceHeight * .23,
        cx - faceWidth * .015,
        eyeY + faceHeight * .25,
      );
    canvas.drawPath(
      nose,
      Paint()
        ..color = const Color(0xFF83594A).withValues(alpha: .7)
        ..strokeWidth = math.max(1.0, size.height * .015).toDouble()
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke,
    );

    final mouthY = faceTop + faceHeight * .755;
    final mouth = Path()
      ..moveTo(cx - faceWidth * .19, mouthY)
      ..quadraticBezierTo(
        cx - faceWidth * .08,
        mouthY - faceHeight * .055,
        cx,
        mouthY - faceHeight * .012,
      )
      ..quadraticBezierTo(
        cx + faceWidth * .08,
        mouthY - faceHeight * .055,
        cx + faceWidth * .19,
        mouthY,
      )
      ..quadraticBezierTo(
        cx,
        mouthY + faceHeight * .105,
        cx - faceWidth * .19,
        mouthY,
      )
      ..close();
    canvas.drawPath(mouth, Paint()..color = lip);
    canvas.drawPath(
      Path()
        ..moveTo(cx - faceWidth * .13, mouthY + faceHeight * .015)
        ..quadraticBezierTo(cx, mouthY + faceHeight * .055, cx + faceWidth * .13, mouthY + faceHeight * .015),
      Paint()
        ..color = const Color(0xFFFFDFD8).withValues(alpha: .8)
        ..strokeWidth = math.max(1.0, size.height * .012).toDouble()
        ..style = PaintingStyle.stroke,
    );

    if (name.contains('glasses')) {
      final glasses = Paint()
        ..color = const Color(0xFF3F3649)
        ..strokeWidth = math.max(1.0, size.height * .025).toDouble()
        ..style = PaintingStyle.stroke;
      for (final side in const [-1.0, 1.0]) {
        final center = Offset(cx + side * faceWidth * .225, eyeY);
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromCenter(center: center, width: eyeWidth * 1.75, height: eyeHeight * 2.55),
            Radius.circular(eyeHeight * .55),
          ),
          glasses,
        );
      }
      canvas.drawLine(
        Offset(cx - eyeWidth * .1, eyeY),
        Offset(cx + eyeWidth * .1, eyeY),
        glasses,
      );
    }

    if (name.contains('beard')) {
      final beard = Path()
        ..moveTo(cx - faceWidth * .42, faceTop + faceHeight * .63)
        ..quadraticBezierTo(
          cx - faceWidth * .31,
          faceRect.bottom + faceHeight * .05,
          cx,
          faceTop + faceHeight * .91,
        )
        ..quadraticBezierTo(
          cx + faceWidth * .31,
          faceRect.bottom + faceHeight * .05,
          cx + faceWidth * .42,
          faceTop + faceHeight * .63,
        )
        ..quadraticBezierTo(
          cx,
          faceTop + faceHeight * .78,
          cx - faceWidth * .42,
          faceTop + faceHeight * .63,
        )
        ..close();
      canvas.drawPath(beard, Paint()..color = hair.withValues(alpha: .88));
    }

    if (name.contains('age')) {
      final wrinklePaint = Paint()
        ..color = const Color(0xFF885D4C).withValues(alpha: .64)
        ..strokeWidth = math.max(.7, size.height * .009).toDouble()
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;
      for (final side in const [-1.0, 1.0]) {
        final x = cx + side * faceWidth * .22;
        canvas.drawLine(
          Offset(x - faceWidth * .045, eyeY + eyeHeight * 1.6),
          Offset(x + faceWidth * .045, eyeY + eyeHeight * 1.6),
          wrinklePaint,
        );
      }
    }

    final sparkle = Paint()..color = Colors.white.withValues(alpha: .8);
    canvas.drawCircle(Offset(size.width * .14, size.height * .74), size.height * .025, sparkle);
    canvas.drawCircle(Offset(size.width * .86, size.height * .24), size.height * .035, sparkle);
  }

  @override
  bool shouldRepaint(covariant _FaceSamplePainter oldDelegate) =>
      oldDelegate.label != label;
}
