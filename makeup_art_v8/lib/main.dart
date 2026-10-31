import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'pages/admin_page.dart';
import 'pages/beauty_page.dart';
import 'pages/login_page.dart';
import 'pages/subscription_page.dart';
import 'services/api_client.dart';
import 'services/update_service.dart';
import 'widgets/developer_branding.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MakeupArtApp());
}

class MakeupArtApp extends StatefulWidget {
  const MakeupArtApp({super.key});
  @override
  State<MakeupArtApp> createState() => _MakeupArtAppState();
}

class _MakeupArtAppState extends State<MakeupArtApp> {
  late final ApiClient api;
  late final UpdateService updateService;
  final GlobalKey<NavigatorState> _navigatorKey = GlobalKey<NavigatorState>();
  bool ready = false;
  bool authenticated = false;
  bool _updateCheckStarted = false;

  @override
  void initState() {
    super.initState();
    api = ApiClient(onSessionExpired: _onSessionExpired);
    updateService = UpdateService();
    _restoreSession();
  }

  void _onSessionExpired() {
    if (!mounted || !authenticated) return;
    setState(() => authenticated = false);
  }

  Future<void> _restoreSession() async {
    var hasStoredSession = false;
    try {
      hasStoredSession = await api.hasSession();
    } catch (_) {
      // Corrupt/unavailable platform secure storage must not leave the app
      // stuck on the startup spinner. Fail closed and show the sign-in screen.
      try {
        await api.logoutLocal();
      } catch (_) {
        // Some platform storage failures also prevent deletion; startup must
        // still recover to the sign-in screen.
      }
    }

    if (!mounted) return;
    setState(() {
      authenticated = hasStoredSession;
      ready = true;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _checkForAppUpdate();
    });
  }

  Future<void> _checkForAppUpdate() async {
    if (_updateCheckStarted) return;
    _updateCheckStarted = true;

    final update = await updateService.checkForUpdate();
    if (!mounted) return;
    if (update == null) return;

    final navigatorContext = _navigatorKey.currentContext;
    if (navigatorContext == null || !navigatorContext.mounted) return;

    await showDialog<void>(
      context: navigatorContext,
      barrierDismissible: true,
      builder: (dialogContext) => AlertDialog(
        icon: const Icon(Icons.system_update_alt_rounded, size: 36),
        title: const Text('Sasisho jipya la MakeupArt V8'),
        content: Text(
          'Toleo ${update.version} linapatikana. Pakua sasisho ili upate '
          'marekebisho mapya. Android itakuomba uthibitishe kusakinisha.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Baadaye'),
          ),
          FilledButton.icon(
            onPressed: () async {
              Navigator.of(dialogContext).pop();
              try {
                final opened = await launchUrl(
                  update.downloadUri,
                  mode: LaunchMode.externalApplication,
                );
                if (!opened) {
                  final feedbackContext = _navigatorKey.currentContext;
                  if (feedbackContext == null || !feedbackContext.mounted) {
                    return;
                  }
                  ScaffoldMessenger.of(feedbackContext).showSnackBar(
                    const SnackBar(
                      content: Text(
                        'Imeshindwa kufungua upakuaji. Jaribu tena baadaye.',
                      ),
                    ),
                  );
                }
              } catch (_) {
                final feedbackContext = _navigatorKey.currentContext;
                if (feedbackContext == null || !feedbackContext.mounted) {
                  return;
                }
                ScaffoldMessenger.of(feedbackContext).showSnackBar(
                  const SnackBar(
                    content: Text('Imeshindwa kufungua link ya sasisho.'),
                  ),
                );
              }
            },
            icon: const Icon(Icons.download_rounded),
            label: const Text('Pakua sasisho'),
          ),
        ],
      ),
    );
  }

  Future<void> _logout() async {
    await api.logout();
    if (mounted) setState(() => authenticated = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!ready) {
      return MaterialApp(
        debugShowCheckedModeBanner: false,
        title: 'MakeupArt V8',
        theme: ThemeData(
          useMaterial3: true,
          brightness: Brightness.dark,
          colorSchemeSeed: const Color(0xFFB66DFF),
          scaffoldBackgroundColor: const Color(0xFF090B12),
        ),
        home: const Scaffold(
          body: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.auto_awesome, size: 64),
                SizedBox(height: 16),
                Text(
                  'MakeupArt V8',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
                ),
                SizedBox(height: 6),
                DeveloperBranding(centered: true),
                SizedBox(height: 20),
                SizedBox(
                  width: 28,
                  height: 28,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return MaterialApp(
      navigatorKey: _navigatorKey,
      debugShowCheckedModeBanner: false,
      title: 'MakeupArt V8',
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorSchemeSeed: const Color(0xFFB66DFF),
        scaffoldBackgroundColor: const Color(0xFF090B12),
      ),
      home: authenticated
          ? SessionGate(api: api, onLogout: _logout)
          : LoginPage(
              api: api,
              onLoggedIn: () => setState(() => authenticated = true),
            ),
    );
  }
}

class SessionGate extends StatefulWidget {
  const SessionGate({super.key, required this.api, required this.onLogout});

  final ApiClient api;
  final VoidCallback onLogout;

  @override
  State<SessionGate> createState() => _SessionGateState();
}

class _SessionGateState extends State<SessionGate> {
  bool loading = true;
  Map<String, dynamic>? user;
  Map<String, dynamic>? subscription;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _sessionLoadError(DioException exception) {
    if (exception.type == DioExceptionType.connectionTimeout ||
        exception.type == DioExceptionType.sendTimeout ||
        exception.type == DioExceptionType.receiveTimeout) {
      return 'The server is waking up or responding slowly. Keep your internet connected and try again.';
    }

    final statusCode = exception.response?.statusCode;
    final data = exception.response?.data;
    final detail = data is Map ? data['detail'] : null;

    if (statusCode == 403) {
      return 'Your account is inactive or access is restricted. Contact support.';
    }
    if (statusCode != null && statusCode >= 500) {
      final requestId =
          data is Map ? data['request_id']?.toString().trim() : null;
      if (requestId != null && requestId.isNotEmpty) {
        return 'The server could not load your account. Try again later. Support reference: $requestId.';
      }
      return 'The server could not load your account. Try again later.';
    }
    if (exception.response == null) {
      return 'Cannot reach the MakeupArt server. Check your internet connection and try again.';
    }
    if (detail is String && detail.trim().isNotEmpty) {
      return detail.trim();
    }
    return 'Could not load account status. Please sign out and try again.';
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        loading = true;
        error = null;
      });
    }
    try {
      final currentUser = await widget.api.currentUser();
      user = currentUser;
      if (currentUser['is_platform_admin'] != true) {
        subscription = await widget.api.getSubscription();
      }
    } on DioException catch (exception) {
      if (exception.response?.statusCode == 401) {
        // The API interceptor clears tokens when refresh fails. Return to the
        // login screen instead of leaving users trapped on a stale-session page.
        await widget.api.logoutLocal();
        if (mounted) widget.onLogout();
        return;
      }
      error = _sessionLoadError(exception);
    } catch (_) {
      error = 'Could not load account status. Check your connection and try again.';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (error != null) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(error!, textAlign: TextAlign.center),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: loading ? null : _load,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Retry connection'),
                ),
                const SizedBox(height: 8),
                OutlinedButton(
                  onPressed: loading ? null : widget.onLogout,
                  child: const Text('Sign out'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (user?['is_platform_admin'] == true) {
      return AdminPage(api: widget.api, onLogout: widget.onLogout);
    }

    final status = subscription?['status']?.toString().toLowerCase();
    if (status != 'active' && status != 'trialing') {
      return SubscriptionPage(
        subscription: subscription ?? const {},
        onLogout: widget.onLogout,
        onRetry: _load,
        loading: loading,
      );
    }

    final salonId = user?['salon_id']?.toString();
    if (salonId == null || salonId.isEmpty) {
      return const Scaffold(
        body: Center(
          child: Text('Account is missing a salon profile.'),
        ),
      );
    }

    final role = user?['role']?.toString().toLowerCase();
    final canManageBranding = role == 'owner' || role == 'admin';

    return BeautyPage(
      api: widget.api,
      onLogout: widget.onLogout,
      salonId: salonId,
      canManageBranding: canManageBranding,
    );
  }
}
