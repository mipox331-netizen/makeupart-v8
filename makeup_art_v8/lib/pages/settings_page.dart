import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../services/api_client.dart';
import '../widgets/license_page_button.dart';
import 'branding_settings_page.dart';

class MakeupArtSettingsPage extends StatefulWidget {
  const MakeupArtSettingsPage({
    super.key,
    required this.api,
    required this.canManageBranding,
    required this.onLogout,
  });

  final ApiClient api;
  final bool canManageBranding;
  final VoidCallback onLogout;

  @override
  State<MakeupArtSettingsPage> createState() => _MakeupArtSettingsPageState();
}

class _MakeupArtSettingsPageState extends State<MakeupArtSettingsPage> {
  Map<String, dynamic>? _user;
  Map<String, dynamic>? _salon;
  Map<String, dynamic>? _subscription;
  PackageInfo? _packageInfo;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait<dynamic>([
        widget.api.currentUser(),
        PackageInfo.fromPlatform(),
        if (widget.canManageBranding) widget.api.getSalonProfile(),
        widget.api.getSubscription(),
      ]);
      if (!mounted) return;
      var index = 0;
      final user = Map<String, dynamic>.from(results[index++] as Map);
      final packageInfo = results[index++] as PackageInfo;
      Map<String, dynamic>? salon;
      if (widget.canManageBranding) {
        salon = Map<String, dynamic>.from(results[index++] as Map);
      }
      final subscription = Map<String, dynamic>.from(results[index] as Map);
      setState(() {
        _user = user;
        _packageInfo = packageInfo;
        _salon = salon;
        _subscription = subscription;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _error = 'Could not refresh account settings. Check your connection and try again.';
        });
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirmSignOut() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        icon: const Icon(Icons.logout_rounded),
        title: const Text('Sign out of MakeupArt?'),
        content: const Text(
          'You will need to sign in again to access your salon workspace.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (confirmed == true && mounted) widget.onLogout();
  }

  String _displayName() {
    final fullName = _user?['full_name']?.toString().trim();
    if (fullName != null && fullName.isNotEmpty) return fullName;
    final email = _user?['email']?.toString().trim();
    if (email != null && email.isNotEmpty) return email;
    return 'MakeupArt account';
  }

  String _roleLabel() {
    final role = _user?['role']?.toString().trim();
    if (role == null || role.isEmpty) return 'Salon member';
    return role
        .split('_')
        .map((part) => part.isEmpty
            ? part
            : '${part[0].toUpperCase()}${part.substring(1)}')
        .join(' ');
  }

  void _openBranding() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => BrandingSettingsPage(api: widget.api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final email = _user?['email']?.toString() ?? 'Email unavailable';
    final plan = _subscription?['plan']?.toString();
    final status = _subscription?['status']?.toString();
    final packageInfo = _packageInfo;
    final version = packageInfo == null
        ? 'Loading…'
        : '${packageInfo.version} (${packageInfo.buildNumber})';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          const LicensePageButton(),
          IconButton(
            tooltip: 'Refresh settings',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                children: [
                  if (_error != null) ...[
                    Card(
                      child: ListTile(
                        leading: Icon(Icons.cloud_off_rounded,
                            color: theme.colorScheme.error),
                        title: const Text('Settings could not refresh'),
                        subtitle: Text(_error!),
                        trailing: IconButton(
                          tooltip: 'Try again',
                          onPressed: _load,
                          icon: const Icon(Icons.refresh_rounded),
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                  ],
                  Card(
                    clipBehavior: Clip.antiAlias,
                    child: Container(
                      decoration: const BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [Color(0xFF38234E), Color(0xFF171B2B)],
                        ),
                      ),
                      padding: const EdgeInsets.all(20),
                      child: Row(
                        children: [
                          CircleAvatar(
                            radius: 28,
                            backgroundColor: Colors.white.withValues(alpha: .14),
                            child: const Icon(Icons.person_rounded, size: 30),
                          ),
                          const SizedBox(width: 14),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _displayName(),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: theme.textTheme.titleLarge?.copyWith(
                                    fontWeight: FontWeight.w800,
                                    color: Colors.white,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  email,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: theme.textTheme.bodyMedium?.copyWith(
                                    color: Colors.white70,
                                  ),
                                ),
                                const SizedBox(height: 5),
                                Text(
                                  _roleLabel(),
                                  style: theme.textTheme.labelMedium?.copyWith(
                                    color: Colors.white70,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),
                  _sectionTitle(context, 'ACCOUNT'),
                  Card(
                    child: Column(
                      children: [
                        ListTile(
                          leading: const Icon(Icons.workspace_premium_outlined),
                          title: const Text('Salon plan'),
                          subtitle: Text(
                            '${plan == null || plan.isEmpty ? 'Not available' : plan.toUpperCase()}'
                            '${status == null || status.isEmpty ? '' : ' · ${status.toUpperCase()}'}',
                          ),
                        ),
                        const Divider(height: 1, indent: 56),
                        ListTile(
                          leading: const Icon(Icons.badge_outlined),
                          title: const Text('Account role'),
                          subtitle: Text(_roleLabel()),
                        ),
                      ],
                    ),
                  ),
                  if (widget.canManageBranding) ...[
                    const SizedBox(height: 20),
                    _sectionTitle(context, 'SALON & BRAND'),
                    Card(
                      child: ListTile(
                        leading: const Icon(Icons.storefront_outlined),
                        title: const Text('Salon profile & watermark'),
                        subtitle: Text(
                          _salon?['name']?.toString().trim().isNotEmpty == true
                              ? '${_salon!['name']} · Logo, watermark position and contact details'
                              : 'Business identity, logo, watermark position and contact details',
                        ),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: _openBranding,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  _sectionTitle(context, 'PRIVACY & STORAGE'),
                  const Card(
                    child: Column(
                      children: [
                        ListTile(
                          leading: Icon(Icons.verified_user_outlined),
                          title: Text('Client photo consent'),
                          subtitle: Text(
                            'Confirm that a client has agreed before selecting and processing their portrait.',
                          ),
                        ),
                        Divider(height: 1, indent: 56),
                        ListTile(
                          leading: Icon(Icons.photo_library_outlined),
                          title: Text('Recent results'),
                          subtitle: Text(
                            'The app keeps up to 10 latest results in its in-app history. Saved exports can also be stored in your phone Gallery.',
                          ),
                        ),
                        Divider(height: 1, indent: 56),
                        ListTile(
                          leading: Icon(Icons.lock_outline_rounded),
                          title: Text('Account security'),
                          subtitle: Text(
                            'Your session credentials are stored using secure platform storage. Sign out when using a shared device.',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  _sectionTitle(context, 'APP'),
                  Card(
                    child: Column(
                      children: [
                        ListTile(
                          leading: const Icon(Icons.info_outline_rounded),
                          title: const Text('MakeupArt V8'),
                          subtitle: Text('Version $version'),
                        ),

                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Card(
                    child: ListTile(
                      leading: Icon(Icons.logout_rounded,
                          color: theme.colorScheme.error),
                      title: Text(
                        'Sign out',
                        style: TextStyle(color: theme.colorScheme.error),
                      ),
                      subtitle: const Text('Sign out of this device'),
                      trailing: const Icon(Icons.chevron_right_rounded),
                      onTap: _confirmSignOut,
                    ),
                  ),
                  const SizedBox(height: 14),
                  Center(
                    child: Text(
                      'MAKEUPART V8',
                      style: theme.textTheme.labelSmall?.copyWith(
                        letterSpacing: 2,
                        color: theme.colorScheme.onSurfaceVariant,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _sectionTitle(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              letterSpacing: 1.3,
              fontWeight: FontWeight.w800,
              color: Theme.of(context).colorScheme.primary,
            ),
      ),
    );
  }
}
