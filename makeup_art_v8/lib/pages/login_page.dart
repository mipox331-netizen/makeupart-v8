import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../services/api_client.dart';
import 'register_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key, required this.api, required this.onLoggedIn});
  final ApiClient api;
  final VoidCallback onLoggedIn;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final email = TextEditingController();
  final password = TextEditingController();
  bool loading = false;
  String? error;

  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  String _loginError(Object exception) {
    if (exception is! DioException) {
      return 'Could not sign in. Please try again.';
    }

    final statusCode = exception.response?.statusCode;
    final data = exception.response?.data;
    final detail = data is Map ? data['detail'] : null;

    if (statusCode == 401) {
      return 'Incorrect email or password.';
    }
    if (statusCode == 429) {
      return 'Too many failed login attempts. Please try again in 15 minutes.';
    }
    if (statusCode == 403) {
      return 'Your account has been deactivated. Contact support.';
    }
    if (detail is String && detail.trim().isNotEmpty) {
      return detail.trim();
    }
    if (exception.response == null) {
      return 'Cannot reach the MakeupArt server. Check your internet connection and try again.';
    }
    if (statusCode != null && statusCode >= 500) {
      return 'The server encountered an error. Please try again shortly.';
    }
    return 'Sign in was rejected. Check your email and password, then try again.';
  }

  Future<void> submit() async {
    if (email.text.trim().isEmpty || password.text.isEmpty) {
      setState(() => error = 'Enter your email and password.');
      return;
    }
    setState(() { loading = true; error = null; });
    try {
      try {
        await widget.api.login(email.text.trim(), password.text);
      } catch (exception) {
        if (mounted) {
          setState(() => error = _loginError(exception));
        }
        return;
      }
      widget.onLoggedIn();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: Padding(
              padding: const EdgeInsets.all(28),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.auto_awesome, size: 64),
                  const SizedBox(height: 18),
                  Text(
                    'MakeupArt V8',
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .headlineMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  const Text('AI beauty studio', textAlign: TextAlign.center),
                  const SizedBox(height: 36),
                  TextField(
                    controller: email,
                    keyboardType: TextInputType.emailAddress,
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: password,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Password',
                      prefixIcon: Icon(Icons.lock_outline),
                    ),
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 14),
                    Text(
                      error!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                  const SizedBox(height: 22),
                  FilledButton(
                    onPressed: loading ? null : submit,
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: loading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Sign in'),
                    ),
                  ),
                  const SizedBox(height: 10),
                  TextButton(
                    onPressed: loading
                        ? null
                        : () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => RegisterPage(
                                  api: widget.api,
                                  onRegistered: widget.onLoggedIn,
                                ),
                              ),
                            );
                          },
                    child: const Text('Create salon account'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
