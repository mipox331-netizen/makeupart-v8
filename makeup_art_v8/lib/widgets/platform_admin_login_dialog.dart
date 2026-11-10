import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';

class PlatformAdminLoginDialog extends StatefulWidget {
  const PlatformAdminLoginDialog({
    super.key,
    required this.api,
    required this.onAuthenticated,
  });

  final ApiClient api;
  final VoidCallback onAuthenticated;

  static Future<void> show(
    BuildContext context, {
    required ApiClient api,
    required VoidCallback onAuthenticated,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => PlatformAdminLoginDialog(
        api: api,
        onAuthenticated: onAuthenticated,
      ),
    );
  }

  @override
  State<PlatformAdminLoginDialog> createState() =>
      _PlatformAdminLoginDialogState();
}

class _PlatformAdminLoginDialogState extends State<PlatformAdminLoginDialog> {
  final _username = TextEditingController(text: 'MR AI');
  final _password = TextEditingController();
  bool _passwordVisible = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  String _message(Object exception) {
    if (exception is DioException) {
      final status = exception.response?.statusCode;
      final data = exception.response?.data;
      final detail = data is Map ? data['detail']?.toString() : null;
      if (status == 429) {
        return 'Majaribio yamezidi. Jaribu tena baada ya dakika 15.';
      }
      if (status == 503) {
        return detail?.isNotEmpty == true
            ? detail!
            : 'Dashboard haijawezeshwa kwenye server bado.';
      }
      if (status == 401) return 'Jina la kuingia au password si sahihi.';
      if (status == 403) return 'Akaunti ya admin imesimamishwa.';
      if (exception.response == null) {
        return 'Server haipatikani. Hakikisha intaneti kisha jaribu tena.';
      }
      if (detail?.isNotEmpty == true) return detail!;
    }
    return 'Imeshindwa kuingia kwenye dashboard. Jaribu tena.';
  }

  Future<void> _submit() async {
    if (_username.text.trim().isEmpty || _password.text.isEmpty) {
      setState(() => _error = 'Jaza jina la kuingia na password.');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.loginAsPlatformAdmin(
        username: _username.text.trim(),
        password: _password.text,
      );
      if (!mounted) return;
      Navigator.of(context).pop();
      widget.onAuthenticated();
    } catch (exception) {
      if (mounted) setState(() => _error = _message(exception));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      icon: const Icon(Icons.admin_panel_settings_rounded, size: 34),
      title: const Text('MOOG 343 Dashboard'),
      content: SizedBox(
        width: 360,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'Admin access',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _username,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(
                labelText: 'Login name',
                prefixIcon: Icon(Icons.person_outline_rounded),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: !_passwordVisible,
              textInputAction: TextInputAction.done,
              onSubmitted: (_) => _loading ? null : _submit(),
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock_outline_rounded),
                suffixIcon: IconButton(
                  tooltip: _passwordVisible ? 'Ficha password' : 'Onyesha password',
                  onPressed: () => setState(
                    () => _passwordVisible = !_passwordVisible,
                  ),
                  icon: Icon(
                    _passwordVisible
                        ? Icons.visibility_off_rounded
                        : Icons.visibility_rounded,
                  ),
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  _error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Funga'),
        ),
        FilledButton.icon(
          onPressed: _loading ? null : _submit,
          icon: _loading
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.lock_open_rounded),
          label: const Text('Ingia'),
        ),
      ],
    );
  }
}
