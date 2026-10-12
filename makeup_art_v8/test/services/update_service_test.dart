import 'package:flutter_test/flutter_test.dart';
import 'package:makeup_art_v8/services/update_service.dart';

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
}
