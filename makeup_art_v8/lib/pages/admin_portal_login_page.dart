import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../services/api_client.dart';

class AdminPortalLoginPage extends StatefulWidget {
  const AdminPortalLoginPage({
    super.key,
    required this.api,
    required this.onLoggedIn,
  });

  final ApiClient api;
  final VoidCallback onLoggedIn;

  @override
  State<AdminPortalLoginPage> createState() => _AdminPortalLoginPageState();
}

class _AdminPortalLoginPageState extends State<AdminPortalLoginPage> {
  final _passphrase = TextEditingController();
  bool _passwordVisible = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _passphrase.dispose();
    super.dispose();
  }

  String _messageFor(Object exception) {
    if (exception is! DioException) {
      return 'Imeshindwa kufungua dashboard. Jaribu tena.';
    }
    final status = exception.response?.statusCode;
    if (status == 401) {
      return 'Neno la siri si sahihi.';
    }
    if (status == 429) {
      return 'Majaribio mengi yamefanyika. Subiri dakika 15 kisha ujaribu tena.';
    }
    if (status == 503) {
      return 'Dashboard bado haijaunganishwa kikamilifu na server.';
    }
    if (exception.response == null) {
      return 'Server haipatikani. Hakikisha intaneti kisha jaribu tena.';
    }
    return 'Imeshindwa kuthibitisha ruhusa ya dashboard.';
  }

  Future<void> _submit() async {
    if (_passphrase.text.trim().isEmpty) {
      setState(() => _error = 'Andika neno la siri.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.adminPortalLogin(_passphrase.text);
      if (!mounted) return;
      widget.onLoggedIn();
    } catch (exception) {
      if (mounted) setState(() => _error = _messageFor(exception));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('MR AI · Secure Dashboard'),
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: ListView(
              shrinkWrap: true,
              padding: const EdgeInsets.all(24),
              children: [
                Container(
                  width: 76,
                  height: 76,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFFE9AFC5), Color(0xFF8E75C5)],
                    ),
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: const Icon(
                    Icons.admin_panel_settings_rounded,
                    size: 38,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 18),
                Text(
                  'MR AI',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: 1.2,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Eneo la siri la msimamizi wa MakeupArt',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                ),
                const SizedBox(height: 28),
                TextField(
                  key: const ValueKey('admin-portal-passphrase-input'),
                  controller: _passphrase,
                  obscureText: !_passwordVisible,
                  autocorrect: false,
                  enableSuggestions: false,
                  textInputAction: TextInputAction.done,
                  onSubmitted: _loading ? null : (_) => _submit(),
                  decoration: InputDecoration(
                    labelText: 'Neno la siri',
                    prefixIcon: const Icon(Icons.lock_outline_rounded),
                    suffixIcon: IconButton(
                      key: const ValueKey('admin-portal-password-visibility-toggle'),
                      tooltip: _passwordVisible ? 'Ficha neno la siri' : 'Onyesha neno la siri',
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
                  Text(
                    _error!,
                    key: const ValueKey('admin-portal-login-error'),
                    textAlign: TextAlign.center,
                    style: TextStyle(color: colors.error),
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton.icon(
                  onPressed: _loading ? null : _submit,
                  icon: _loading
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.lock_open_rounded),
                  label: Text(_loading ? 'Inathibitisha…' : 'Ingia dashboard'),
                ),
                const SizedBox(height: 14),
                Text(
                  'Ufikiaji huu unathibitishwa na server na unafunguliwa kwa akaunti ya platform admin pekee.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
