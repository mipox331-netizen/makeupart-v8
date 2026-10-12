import 'package:dio/dio.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// Metadata for a newer public Android release.
class AppUpdate {
  const AppUpdate({
    required this.version,
    required this.downloadUri,
    required this.releaseNotesUri,
  });

  final String version;
  final Uri downloadUri;
  final Uri releaseNotesUri;
}

/// Checks GitHub Releases without blocking app startup or authentication.
class UpdateService {
  UpdateService({Dio? dio})
      : _dio = dio ??
            Dio(
              BaseOptions(
                connectTimeout: const Duration(seconds: 5),
                receiveTimeout: const Duration(seconds: 5),
                sendTimeout: const Duration(seconds: 5),
                headers: const {
                  'Accept': 'application/vnd.github+json',
                  'X-GitHub-Api-Version': '2022-11-28',
                  'User-Agent': 'MakeupArt-V8-Android',
                },
              ),
            );

  static final Uri _latestReleaseUri = Uri.https(
    'api.github.com',
    '/repos/mipox331-netizen/makeupart-v8/releases/latest',
  );

  static const String _expectedAssetName = 'MakeupArt-V8.apk';

  final Dio _dio;

  /// Returns a newer verified GitHub APK release, or null when current/offline.
  ///
  /// Errors are intentionally non-fatal: update checks must never prevent
  /// registration, login, or normal app use when GitHub is unavailable.
  Future<AppUpdate?> checkForUpdate() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      final response = await _dio.getUri(_latestReleaseUri);
      final payload = response.data;
      if (payload is! Map) return null;

      final rawTag = payload['tag_name'];
      final rawReleaseUrl = payload['html_url'];
      final rawAssets = payload['assets'];
      if (rawTag is! String ||
          rawReleaseUrl is! String ||
          rawAssets is! List) {
        return null;
      }

      final versionMatch = RegExp(r'^v?(\d+(?:\.\d+){1,3})$')
          .firstMatch(rawTag.trim());
      if (versionMatch == null) return null;

      final latestVersion = versionMatch.group(1)!;
      if (compareVersions(latestVersion, packageInfo.version) <= 0) {
        return null;
      }

      String? downloadUrl;
      for (final asset in rawAssets) {
        if (asset is Map &&
            asset['name'] == _expectedAssetName &&
            asset['browser_download_url'] is String) {
          downloadUrl = asset['browser_download_url'] as String;
          break;
        }
      }
      if (downloadUrl == null) return null;

      final downloadUri = Uri.tryParse(downloadUrl);
      final releaseNotesUri = Uri.tryParse(rawReleaseUrl);
      if (!_isExpectedGitHubReleaseAsset(downloadUri) ||
          releaseNotesUri == null ||
          releaseNotesUri.scheme != 'https' ||
          releaseNotesUri.host != 'github.com' ||
          !releaseNotesUri.path.startsWith('/mipox331-netizen/makeupart-v8/releases/')) {
        return null;
      }

      return AppUpdate(
        version: latestVersion,
        downloadUri: downloadUri!,
        releaseNotesUri: releaseNotesUri,
      );
    } catch (_) {
      return null;
    }
  }

  static bool _isExpectedGitHubReleaseAsset(Uri? uri) {
    return uri != null &&
        uri.scheme == 'https' &&
        uri.host == 'github.com' &&
        uri.path.startsWith(
          '/mipox331-netizen/makeupart-v8/releases/download/',
        ) &&
        uri.path.endsWith('/$_expectedAssetName');
  }

  /// Numeric dotted-version comparison (for example, 8.0.134 > 8.0.133).
  /// A malformed version compares as equal to avoid a false update prompt.
  static int compareVersions(String left, String right) {
    List<int>? parse(String value) {
      final normalized =
          value.trim().replaceFirst(RegExp(r'^[vV]'), '').split('+').first;
      final versionCore = normalized.split('-').first;
      final parts = versionCore.split('.');
      if (parts.isEmpty ||
          parts.any((part) => !RegExp(r'^\d+$').hasMatch(part))) {
        return null;
      }
      return parts.map(int.parse).toList(growable: false);
    }

    final leftParts = parse(left);
    final rightParts = parse(right);
    if (leftParts == null || rightParts == null) return 0;

    final length = leftParts.length > rightParts.length
        ? leftParts.length
        : rightParts.length;
    for (var index = 0; index < length; index++) {
      final leftPart = index < leftParts.length ? leftParts[index] : 0;
      final rightPart = index < rightParts.length ? rightParts[index] : 0;
      if (leftPart != rightPart) return leftPart.compareTo(rightPart);
    }
    return 0;
  }
}
