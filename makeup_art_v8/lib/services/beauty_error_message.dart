import 'package:dio/dio.dart';

/// Converts API failures from the beauty-processing flow into safe,
/// actionable messages. Never expose server traces, filesystem paths or SQL.
String beautyProcessingErrorMessage(Object exception) {
  if (exception is! DioException) {
    final message = exception.toString().toLowerCase();
    if (message.contains('external generative ai provider')) {
      return 'Confirm that the client agrees to external AI processing.';
    }
    if (message.contains('generative makeup is not enabled')) {
      return 'Generative AI is not configured on the server. Classic AI is still available.';
    }
    if (message.contains('consent')) {
      return 'Client consent is required before processing.';
    }
    return 'Could not process this image. Please try another clear portrait.';
  }

  if (exception.type == DioExceptionType.connectionTimeout ||
      exception.type == DioExceptionType.sendTimeout ||
      exception.type == DioExceptionType.receiveTimeout) {
    return 'The server is waking up or responding slowly. Keep your internet connected and try processing again.';
  }

  final status = exception.response?.statusCode;
  final payload = exception.response?.data;
  final detail = payload is Map ? payload['detail']?.toString().trim() : null;
  final normalizedDetail = detail?.toLowerCase() ?? '';

  if (normalizedDetail.contains('external generative ai provider')) {
    return 'Confirm that the client agrees to external AI processing.';
  }
  if (normalizedDetail.contains('generative makeup is not enabled')) {
    return 'Generative AI is not configured on the server. Classic AI is still available.';
  }
  if (normalizedDetail.contains('consent')) {
    return 'Client consent is required before processing.';
  }

  if (exception.response == null) {
    return 'Cannot reach the MakeupArt server. Check your internet connection and try again.';
  }

  if (status == 401) {
    return 'Your session has expired. Sign in again to continue.';
  }
  if (status == 403) {
    final requiredPlan =
        exception.response?.headers.value('x-required-plan')?.trim();
    if (requiredPlan != null && requiredPlan.isNotEmpty) {
      return 'This editing option requires the ${requiredPlan.toUpperCase()} plan.';
    }
    return 'This editing option is not available for the current salon plan.';
  }
  if (status == 413) {
    return 'This photo is too large. Choose a smaller image and try again.';
  }
  if (status == 415) {
    return 'This photo format is not supported. Choose a JPEG, PNG or WebP image.';
  }
  if (status == 422) {
    if (detail != null &&
        detail.isNotEmpty &&
        detail.length <= 220 &&
        !_containsInternalDetail(normalizedDetail)) {
      return detail;
    }
    return 'The photo could not be processed. Use a clear, front-facing portrait with one visible face.';
  }
  if (status == 429) {
    return 'The salon has reached its processing limit for this period. Check the plan and remaining usage.';
  }
  if (status == 503) {
    if (normalizedDetail.contains('private') ||
        normalizedDetail.contains('storage') ||
        normalizedDetail.contains('logo')) {
      return 'Private photo storage or the salon watermark is temporarily unavailable. The photo was not saved; try again later.';
    }
    return 'The beauty service is temporarily unavailable. Please try again shortly.';
  }
  if (status != null && status >= 500) {
    final requestId =
        payload is Map ? payload['request_id']?.toString().trim() : null;
    if (requestId != null &&
        requestId.isNotEmpty &&
        requestId.length <= 80 &&
        RegExp(r'^[A-Za-z0-9._-]+$').hasMatch(requestId)) {
      return 'The server could not process this photo. Support reference: $requestId.';
    }
    return 'The server could not process this photo. Please try again shortly.';
  }

  if (detail != null &&
      detail.isNotEmpty &&
      detail.length <= 180 &&
      !_containsInternalDetail(normalizedDetail)) {
    return detail;
  }
  return 'Could not process this image. Check the photo and try again.';
}

bool _containsInternalDetail(String detail) {
  return detail.contains('traceback') ||
      detail.contains('sqlalchemy') ||
      detail.contains('integrityerror') ||
      detail.contains('stack trace') ||
      detail.contains('file "') ||
      detail.contains(' at /') ||
      detail.contains('database') ||
      detail.contains('exception:');
}
