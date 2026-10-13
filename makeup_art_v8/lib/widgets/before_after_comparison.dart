import 'package:flutter/material.dart';

/// An accessible, draggable visual comparison of an original and edited photo.
class BeforeAfterComparison extends StatefulWidget {
  const BeforeAfterComparison({
    super.key,
    required this.before,
    required this.after,
    this.height = 360,
  });

  final Widget before;
  final Widget after;
  final double height;

  @override
  State<BeforeAfterComparison> createState() => _BeforeAfterComparisonState();
}

class _BeforeAfterComparisonState extends State<BeforeAfterComparison> {
  double _position = 0.5;

  void _setPosition(double x, double width) {
    if (width <= 0) return;
    setState(() => _position = (x / width).clamp(0.0, 1.0).toDouble());
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Before and after photo comparison. Drag the divider horizontally.',
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          if (width <= 0) return const SizedBox.shrink();

          final handleMaxLeft = (width - 44).clamp(0.0, width).toDouble();
          final handleLeft =
              (width * _position - 22).clamp(0.0, handleMaxLeft).toDouble();
          final handleTop =
              ((widget.height - 44) / 2).clamp(0.0, widget.height).toDouble();

          return ClipRRect(
            borderRadius: BorderRadius.circular(18),
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTapDown: (details) => _setPosition(details.localPosition.dx, width),
              onHorizontalDragUpdate: (details) =>
                  _setPosition(_position * width + details.delta.dx, width),
              child: SizedBox(
                width: double.infinity,
                height: widget.height,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    Container(
                      color: const Color(0xFF10131D),
                      child: widget.after,
                    ),
                    ClipRect(
                      clipper: _BeforeImageClipper(_position),
                      child: Container(
                        color: const Color(0xFF10131D),
                        child: widget.before,
                      ),
                    ),
                    Positioned(
                      left: width * _position - 1,
                      top: 0,
                      bottom: 0,
                      child: const SizedBox(
                        width: 2,
                        child: DecoratedBox(
                          decoration: BoxDecoration(color: Colors.white),
                        ),
                      ),
                    ),
                    Positioned(
                      left: handleLeft,
                      top: handleTop,
                      child: Container(
                        key: const ValueKey('before-after-handle'),
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: Colors.black.withValues(alpha: 0.28),
                              blurRadius: 12,
                              offset: const Offset(0, 3),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.drag_indicator_rounded,
                          color: Color(0xFF44255C),
                          size: 26,
                        ),
                      ),
                    ),
                    Positioned(
                      left: 12,
                      top: 12,
                      child: _ComparisonLabel(
                        text: 'BEFORE',
                        background: Colors.black.withValues(alpha: 0.66),
                      ),
                    ),
                    const Positioned(
                      right: 12,
                      top: 12,
                      child: _ComparisonLabel(
                        text: 'AFTER',
                        background: Color(0xFF44255C),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ComparisonLabel extends StatelessWidget {
  const _ComparisonLabel({
    required this.text,
    required this.background,
  });

  final String text;
  final Color background;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(99),
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
          child: Text(
            text,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ),
      ),
    );
  }
}

class _BeforeImageClipper extends CustomClipper<Rect> {
  const _BeforeImageClipper(this.position);

  final double position;

  @override
  Rect getClip(Size size) =>
      Rect.fromLTWH(0, 0, size.width * position, size.height);

  @override
  bool shouldReclip(covariant _BeforeImageClipper oldClipper) =>
      oldClipper.position != position;
}
