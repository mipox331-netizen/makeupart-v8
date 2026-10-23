import 'package:flutter/material.dart';

/// Credits MOOG 343 as the creator of MakeupArt V8 without changing the app's
/// own product name.
class DeveloperBranding extends StatelessWidget {
  const DeveloperBranding({
    super.key,
    this.compact = false,
    this.centered = false,
  });

  final bool compact;
  final bool centered;

  static const _logoUrl =
      'https://www.google.com/s2/favicons?domain=moog-digital.blogspot.com&sz=128';

  @override
  Widget build(BuildContext context) {
    final logoSize = compact ? 24.0 : 34.0;
    final captionSize = compact ? 10.0 : 12.0;
    final brandSize = compact ? 12.0 : 14.0;

    final row = Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(compact ? 6 : 9),
          child: Container(
            width: logoSize,
            height: logoSize,
            alignment: Alignment.center,
            color: Colors.white,
            padding: const EdgeInsets.all(2),
            child: Image.network(
              _logoUrl,
              width: logoSize - 4,
              height: logoSize - 4,
              fit: BoxFit.contain,
              errorBuilder: (_, __, ___) => Icon(
                Icons.business_rounded,
                size: logoSize - 8,
                color: const Color(0xFF38234E),
              ),
            ),
          ),
        ),
        SizedBox(width: compact ? 7 : 10),
        Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: centered
              ? CrossAxisAlignment.center
              : CrossAxisAlignment.start,
          children: [
            Text(
              'Imetengenezwa na',
              style: TextStyle(
                fontSize: captionSize,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
                height: 1.1,
              ),
            ),
            const SizedBox(height: 2),
            Text(
              'MOOG 343',
              style: TextStyle(
                fontSize: brandSize,
                fontWeight: FontWeight.w800,
                letterSpacing: .4,
                height: 1.1,
              ),
            ),
          ],
        ),
      ],
    );
    return centered ? Center(child: row) : row;
  }
}
