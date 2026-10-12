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

  static final Uri _releasesUri = Uri.https(
    'api.github.com',
    '/repos/mipox331-netizen/makeupart-v8/releases',
    const {'per_page': '100'},
  );

  static const String _expectedAssetName = 'MakeupArt-V8.apk';

  final Dio _dio;

  /// Returns a newer verified GitHub APK release, or null when current/offline.
  ///
  /// GitHub's /releases/latest follows publication chronology, not semantic
  /// version ordering. Concurrent CI runs can therefore publish v8.0.141 and
  /// v8.0.140 out of order. Select the numerically highest eligible APK release.
  ///
  /// Errors are intentionally non-fatal: update checks must never prevent
  /// registration, login, or normal app use when GitHub is unavailable.
  Future<AppUpdate?> checkForUpdate() async {
    try {
      final packageInfo = await PackageInfo.fromPlatform();
      final response = await _dio.getUri(_releasesUri);
      final payload = response.data;
      if (payload is! List) return null;

      final release = selectLatestPublishedApkRelease(payload);
      if (release == null) return null;

      final version = release['version'] as String;
      if (compareVersions(version, packageInfo.version) <= 0) {
        return null;
      }

      return AppUpdate(
        version: version,
        downloadUri: Uri.parse(release['download_url'] as String),
        releaseNotesUri: Uri.parse(release['release_url'] as String),
      );
    } catch (_) {
      return null;
    }
  }

  /// Selects the highest numeric v8.0.N release with a verified APK asset.
  ///
  /// Exposed as a pure helper so release ordering/security checks are covered
  /// by unit tests without making network calls.
  static Map<String, dynamic>? selectLatestPublishedApkRelease(
    List<dynamic> releases,
  ) {
    Map<String, dynamic>? best;
    String? bestVersion;

    for (final value in releases) {
      if (value is! Map || value['draft'] == true || value['prerelease'] == true) {
        continue;
      }

      final tag = value['tag_name'];
      final releaseUrl = value['html_url'];
      final assets = value['assets'];
      if (tag is! String || releaseUrl is! String || assets is! List) continue;

      final match = RegExp(r'^v?(8\.0\.\d+)$').firstMatch(tag.trim());
      if (match == null) continue;
      final version = match.group(1)!;

      final releaseUri = Uri.tryParse(releaseUrl);
      if (releaseUri == null ||
          releaseUri.scheme != 'https' ||
          releaseUri.host != 'github.com' ||
          !releaseUri.path.startsWith(
            '/mipox331-netizen/makeupart-v8/releases/tag/',
          ) ||
          releaseUri.pathSegments.isEmpty ||
          releaseUri.pathSegments.last != tag) {
        continue;
      }

      String? downloadUrl;
      for (final asset in assets) {
        if (asset is! Map ||
            asset['name'] != _expectedAssetName ||
            asset['browser_download_url'] is! String) {
          continue;
        }
        final assetUri =
            Uri.tryParse(asset['browser_download_url'] as String);
        if (_isExpectedGitHubReleaseAsset(assetUri, tag)) {
          downloadUrl = assetUri!.toString();
          break;
        }
      }
      if (downloadUrl == null) continue;

      if (bestVersion == null ||
          compareVersions(version, bestVersion) > 0) {
        bestVersion = version;
        best = {
          'tag_name': tag,
          'version': version,
          'release_url': releaseUri.toString(),
          'download_url': downloadUrl,
        };
      }
    }

    return best;
  }

  static bool _isExpectedGitHubReleaseAsset(Uri? uri, String tag) {
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host != 'github.com') {
      return false;
    }
    final segments = uri.pathSegments;
    return segments.length == 6 &&
        segments[0] == 'mipox331-netizen' &&
        segments[1] == 'makeupart-v8' &&
        segments[2] == 'releases' &&
        segments[3] == 'download' &&
        segments[4] == tag &&
        segments[5] == _expectedAssetName;
  }

  /// Numeric dotted-version comparison (for example, 8.0.142 > 8.0.141).
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
