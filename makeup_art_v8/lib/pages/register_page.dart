import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';

class RegisterPage extends StatefulWidget {
  const RegisterPage({
    super.key,
    required this.api,
    required this.onRegistered,
  });

  final ApiClient api;
  final VoidCallback onRegistered;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final salonName = TextEditingController();
  final ownerName = TextEditingController();
  final email = TextEditingController();
  final phone = TextEditingController();
  final password = TextEditingController();
  bool loading = false;
  bool accountCreated = false;
  String? error;

  @override
  void dispose() {
    salonName.dispose();
    ownerName.dispose();
    email.dispose();
    phone.dispose();
    password.dispose();
    super.dispose();
  }

  String _registrationError(Object exception) {
    if (exception is! DioException) {
      return 'Could not create the account. Please try again.';
    }

    final statusCode = exception.response?.statusCode;
    final data = exception.response?.data;
    final detail = data is Map ? data['detail'] : null;

    if (statusCode == 409) {
      return 'This email already has an account. Go back and sign in, or use another email.';
    }
    if (statusCode == 422 && detail is List) {
      final messages = detail.whereType<Map>().map((item) {
        final location = item['loc'];
        final field = location is List && location.isNotEmpty
            ? location.last.toString().replaceAll('_', ' ')
            : 'field';
        final message = (item['msg'] ?? 'is invalid').toString();
        return '$field: $message';
      }).toList();
      if (messages.isNotEmpty) {
        return 'Please correct these details: ${messages.join('; ')}';
      }
    }
    if (detail is String && detail.trim().isNotEmpty) {
      return detail.trim();
    }
    if (exception.response == null) {
      return 'Cannot reach the MakeupArt server. Check your internet connection and try again.';
    }
    if (statusCode != null && statusCode >= 500) {
      return 'The server could not create the account just now. Please try again shortly.';
    }
    return 'The account details were rejected. Check the email and password, then try again.';
  }

  Future<void> submit() async {
    if (accountCreated) {
      Navigator.of(context).pop();
      return;
    }

    if (salonName.text.trim().length < 2 ||
        ownerName.text.trim().length < 2 ||
        email.text.trim().isEmpty ||
        password.text.length < 8) {
      setState(() => error = 'Enter a salon name and owner name (at least 2 characters), a valid email, and a password of 8+ characters.');
      return;
    }

    setState(() {
      loading = true;
      error = null;
    });

    try {
      try {
        await widget.api.register(
          salonName: salonName.text.trim(),
          ownerFullName: ownerName.text.trim(),
          email: email.text.trim(),
          password: password.text,
          phone: phone.text,
        );
      } catch (exception) {
        if (mounted) {
          setState(() => error = _registrationError(exception));
        }
        return;
      }

      if (!mounted) return;
      setState(() => accountCreated = true);

      try {
        await widget.api.login(email.text.trim(), password.text);
      } catch (_) {
        if (mounted) {
          setState(() => error = 'Your account was created successfully, but automatic sign-in failed. Go back and sign in using this email and password.');
        }
        return;
      }

      if (!mounted) return;
      Navigator.of(context).pop();
      widget.onRegistered();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  InputDecoration decoration(String label, IconData icon) => InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create salon account')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(28),
          children: [
            const Icon(Icons.storefront_outlined, size: 64),
            const SizedBox(height: 18),
            Text(
              'Start with MakeupArt V8',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 28),
            TextField(
              controller: salonName,
              decoration: decoration('Salon name', Icons.store_outlined),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: ownerName,
              decoration: decoration('Owner full name', Icons.person_outline),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: email,
              keyboardType: TextInputType.emailAddress,
              decoration: decoration('Email', Icons.email_outlined),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: phone,
              keyboardType: TextInputType.phone,
              decoration: decoration('Phone (optional)', Icons.phone_outlined),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: password,
              obscureText: true,
              decoration: decoration('Password', Icons.lock_outline),
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
                    : Text(accountCreated ? 'Back to sign in' : 'Create account'),
              ),
            ),
            if (error != null &&
                (accountCreated || error!.contains('already has an account'))) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: loading ? null : () => Navigator.of(context).pop(),
                child: const Text('Back to sign in'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
