import 'package:flutter/material.dart';

import 'pages/beauty_page.dart';
import 'pages/login_page.dart';
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
          ? BeautyPage(api: api, onLogout: () async {
              await api.logout();
              if (mounted) setState(() => authenticated = false);
            })
          : LoginPage(api: api, onLoggedIn: () => setState(() => authenticated = true)),
    );
  }
}
