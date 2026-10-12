import 'package:flutter/material.dart';

const String makeupArtLegalese =
    'Copyright © 2026 MakeupArt V8. All rights reserved. '
    'Original application source is proprietary. Third-party packages and '
    'platform components remain subject to their own licenses and notices.';

Future<void> showMakeupArtLicenses(BuildContext context) {
  return showLicensePage(
    context: context,
    applicationName: 'MakeupArt V8',
    applicationLegalese: makeupArtLegalese,
    applicationIcon: const Icon(Icons.auto_awesome, size: 36),
  );
}

class LicensePageButton extends StatelessWidget {
  const LicensePageButton({super.key});

  @override
  Widget build(BuildContext context) {
    return IconButton(
      tooltip: 'Open-source licenses',
      icon: const Icon(Icons.policy_outlined),
      onPressed: () => showMakeupArtLicenses(context),
    );
  }
}
