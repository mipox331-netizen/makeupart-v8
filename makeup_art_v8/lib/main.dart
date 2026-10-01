import 'package:flutter/material.dart';

import 'pages/admin_page.dart';
import 'pages/beauty_page.dart';
import 'pages/login_page.dart';
import 'pages/subscription_page.dart';
import 'services/api_client.dart';

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
  final ApiClient api = ApiClient();
  bool ready = false;
  bool authenticated = false;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    authenticated = await api.hasSession();
    if (mounted) setState(() => ready = true);
  }

  Future<void> _logout() async {
    await api.logout();
    if (mounted) setState(() => authenticated = false);
  }

  @override
  Widget build(BuildContext context) {
    if (!ready) {
      return const MaterialApp(
        home: Scaffold(body: Center(child: CircularProgressIndicator())),
      );
    }

    return MaterialApp(
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
    } catch (exception) {
      error = 'Could not load account status: $exception';
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
                const SizedBox(height: 14),
                FilledButton(
                  onPressed: widget.onLogout,
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

    return BeautyPage(
      api: widget.api,
      onLogout: widget.onLogout,
      salonId: salonId,
    );
  }
}
