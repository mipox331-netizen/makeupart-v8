import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/update_service.dart';

Map<String, dynamic> release(
  String version, {
  bool draft = false,
  bool prerelease = false,
  String? downloadUrl,
  bool includeApk = true,
}) {
  final tag = 'v$version';
  final assetUrl = downloadUrl ??
      'https://github.com/mipox331-netizen/makeupart-v8/releases/download/$tag/MakeupArt-V8.apk';
  return {
    'tag_name': tag,
    'html_url': 'https://github.com/mipox331-netizen/makeupart-v8/releases/tag/$tag',
    'draft': draft,
    'prerelease': prerelease,
    'assets': [
      if (includeApk)
        {'name': 'MakeupArt-V8.apk', 'browser_download_url': assetUrl},
    ],
  };
}

void main() {
  group('UpdateService.compareVersions', () {
    test('compares dotted numeric versions numerically', () {
      expect(UpdateService.compareVersions('8.0.134', '8.0.133'), greaterThan(0));
      expect(UpdateService.compareVersions('8.0.9', '8.0.10'), lessThan(0));
      expect(UpdateService.compareVersions('8.1.0', '8.0.999'), greaterThan(0));
    });

    test('accepts release tag prefixes and build metadata', () {
      expect(UpdateService.compareVersions('v8.0.133', '8.0.133+133'), 0);
      expect(UpdateService.compareVersions('8.0.134+134', '8.0.133'), greaterThan(0));
    });

    test('treats equivalent versions as equal', () {
      expect(UpdateService.compareVersions('8.0.133', '8.0.133'), 0);
      expect(UpdateService.compareVersions('8.0', '8.0.0'), 0);
    });

    test('fails closed for malformed version strings', () {
      expect(UpdateService.compareVersions('latest', '8.0.133'), 0);
      expect(UpdateService.compareVersions('8.0.134', 'not-a-version'), 0);
    });
  });

  group('UpdateService.selectLatestPublishedApkRelease', () {
    test('chooses highest numeric version even when publication order differs', () {
      final selected = UpdateService.selectLatestPublishedApkRelease([
        release('8.0.141'),
        release('8.0.140'),
        release('8.0.139'),
      ]);

      expect(selected?['tag_name'], 'v8.0.141');
      expect(selected?['version'], '8.0.141');
      expect(
        selected?['download_url'],
        'https://github.com/mipox331-netizen/makeupart-v8/releases/download/v8.0.141/MakeupArt-V8.apk',
      );
    });

    test('ignores draft and prerelease entries', () {
      final selected = UpdateService.selectLatestPublishedApkRelease([
        release('8.0.150', draft: true),
        release('8.0.149', prerelease: true),
        release('8.0.141'),
      ]);

      expect(selected?['tag_name'], 'v8.0.141');
    });

    test('rejects missing APK and untrusted download locations', () {
      expect(
        UpdateService.selectLatestPublishedApkRelease([
          release('8.0.142', includeApk: false),
        ]),
        isNull,
      );
      expect(
        UpdateService.selectLatestPublishedApkRelease([
          release(
            '8.0.142',
            downloadUrl: 'https://example.com/MakeupArt-V8.apk',
          ),
        ]),
        isNull,
      );
    });

    test('returns null when there is no published app release', () {
      expect(UpdateService.selectLatestPublishedApkRelease([]), isNull);
      expect(
        UpdateService.selectLatestPublishedApkRelease([
          {'tag_name': 'latest', 'assets': []},
        ]),
        isNull,
      );
    });
  });
}
