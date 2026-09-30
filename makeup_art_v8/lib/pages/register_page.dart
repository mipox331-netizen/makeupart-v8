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

  Future<void> submit() async {
    if (salonName.text.trim().isEmpty ||
        ownerName.text.trim().isEmpty ||
        email.text.trim().isEmpty ||
        password.text.length < 8) {
      setState(() => error = 'Fill all required fields. Password must be 8+ characters.');
      return;
    }

    setState(() {
      loading = true;
      error = null;
    });

    try {
      await widget.api.register(
        salonName: salonName.text.trim(),
        ownerFullName: ownerName.text.trim(),
        email: email.text.trim(),
        password: password.text,
        phone: phone.text,
      );
      await widget.api.login(email.text.trim(), password.text);
      if (!mounted) return;
      Navigator.of(context).pop();
      widget.onRegistered();
    } catch (_) {
      if (mounted) {
        setState(() => error = 'Registration failed. Check the details and API connection.');
      }
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
                    : const Text('Create account'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
