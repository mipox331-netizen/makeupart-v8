import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_client.dart';
import 'branding_settings_page.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({
    super.key,
    required this.api,
    required this.salonId,
    required this.subscription,
    required this.canManageBranding,
  });

  final ApiClient api;
  final String salonId;
  final Map<String, dynamic> subscription;
  final bool canManageBranding;

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late Map<String, dynamic> _subscription;
  Map<String, dynamic> _salon = const {};
  String _requestPlan = 'pro';
  int _requestDays = 365;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _subscription = Map<String, dynamic>.from(widget.subscription);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait<Map<String, dynamic>>([
        widget.api.getSubscription(),
        widget.api.getSalonProfile(),
      ]);
      if (!mounted) return;
      setState(() {
        _subscription = results[0];
        _salon = results[1];
      });
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not refresh settings. Showing the last available account status.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _copyUpgradeRequest() async {
    final savedSalonName = _salon['name']?.toString().trim();
    final salonName = savedSalonName == null || savedSalonName.isEmpty
        ? 'Salon ${widget.salonId}'
        : savedSalonName;
    final currentPlan = _subscription['plan']?.toString() ?? 'unknown';
    final request = 'MakeupArt V8 plan activation request\n'
        'Salon: $salonName\n'
        'Current plan: $currentPlan\n'
        'Requested plan: ${_requestPlan.toUpperCase()}\n'
        'Requested term: $_requestDays days\n'
        'Please confirm plan price, payment instructions, and activation date.';
    await Clipboard.setData(ClipboardData(text: request));
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Upgrade request copied. Send it to your platform administrator.'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _openBranding() async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => BrandingSettingsPage(api: widget.api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final plan = (_subscription['plan']?.toString() ?? 'free').toLowerCase();
    final status = (_subscription['status']?.toString() ?? 'unknown').toLowerCase();
    final used = (_subscription['used'] as num?)?.toInt() ?? 0;
    final limit = (_subscription['monthly_limit'] as num?)?.toInt();
    final remaining = (_subscription['remaining'] as num?)?.toInt();
    final usage = limit == null || limit <= 0 ? 0.0 : (used / limit).clamp(0.0, 1.0).toDouble();
    final salonName = _salon['name']?.toString() ?? 'Your salon';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings & business'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF44255C), Color(0xFF191B2D), Color(0xFF10131C)],
              ),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: Colors.white.withValues(alpha: .10)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.settings_suggest_rounded, size: 30),
                const SizedBox(height: 12),
                Text(
                  salonName,
                  style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 6),
                Text(
                  'Manage your subscription, salon identity, photo storage, and client privacy.',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: .78),
                  ),
                ),
              ],
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
          ],
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.workspace_premium_outlined, size: 24),
                      const SizedBox(width: 10),
                      Expanded(child: Text('Current subscription', style: theme.textTheme.titleLarge)),
                      Chip(label: Text(plan.toUpperCase())),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text('Status: ${status.toUpperCase()}'),
                  const SizedBox(height: 12),
                  if (limit == null)
                    Text('$used AI jobs used this month · unlimited plan')
                  else ...[
                    Row(
                      children: [
                        Expanded(child: Text('$used of $limit AI jobs used this month')),
                        Text('${remaining ?? 0} left'),
                      ],
                    ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(value: usage, minHeight: 7),
                  ],
                  if (_subscription['current_period_end'] != null) ...[
                    const SizedBox(height: 10),
                    Text('Plan period ends: ${_subscription['current_period_end']}'),
                  ],
                  const SizedBox(height: 12),
                  Text(
                    _loading
                        ? 'Refreshing account status…'
                        : 'Plan access is checked by the backend, not only by this screen.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Plans & included tools', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 6),
                  const Text(
                    'Free is for trying the workflow. Basic adds higher usage and Soft Glam. Pro unlocks all current makeup presets and photo finishes. Enterprise is for larger salon operations.',
                  ),
                  const SizedBox(height: 14),
                  _PlanRow(
                    name: 'Free',
                    usage: '25 AI jobs / month',
                    features: 'Natural makeup · Natural Finish · Warm Glow',
                    selected: plan == 'free',
                  ),
                  _PlanRow(
                    name: 'Basic',
                    usage: '250 AI jobs / month',
                    features: 'Everything in Free + Soft Glam',
                    selected: plan == 'basic',
                  ),
                  _PlanRow(
                    name: 'Pro',
                    usage: '1,000 AI jobs / month',
                    features: 'Bridal Rose · Evening Glam · Studio Polish · Golden Hour',
                    selected: plan == 'pro',
                  ),
                  _PlanRow(
                    name: 'Enterprise / Salon',
                    usage: 'Unlimited AI jobs',
                    features: 'All current tools · platform-managed activation',
                    selected: plan == 'enterprise',
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Billing truth: automated online checkout is not configured in this deployment. Monthly (30-day) or annual (365-day) access must be confirmed and activated by the platform administrator. No payment is taken from this screen.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: _requestPlan,
                    decoration: const InputDecoration(
                      labelText: 'Request a plan',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'basic', child: Text('Basic')),
                      DropdownMenuItem(value: 'pro', child: Text('Pro')),
                      DropdownMenuItem(value: 'enterprise', child: Text('Enterprise / Salon')),
                    ],
                    onChanged: (value) {
                      if (value != null) setState(() => _requestPlan = value);
                    },
                  ),
                  const SizedBox(height: 12),
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment<int>(value: 30, label: Text('Monthly · 30 days')),
                      ButtonSegment<int>(value: 365, label: Text('Annual · 365 days')),
                    ],
                    selected: {_requestDays},
                    onSelectionChanged: (value) => setState(() => _requestDays = value.first),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _copyUpgradeRequest,
                    icon: const Icon(Icons.copy_all_rounded),
                    label: const Text('Copy plan activation request'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Salon branding', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 6),
                  const Text(
                    'Set your business name, logo, watermark placement, and optional contact handles on new beauty results.',
                  ),
                  const SizedBox(height: 12),
                  if (widget.canManageBranding)
                    FilledButton.icon(
                      onPressed: _openBranding,
                      icon: const Icon(Icons.brush_outlined),
                      label: const Text('Manage logo & watermark'),
                    )
                  else
                    const Text(
                      'Only salon owners or admins can edit branding. Ask the owner to make changes.',
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Photo privacy & consent', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 10),
                  const _PrivacyLine(
                    icon: Icons.cloud_upload_outlined,
                    text: 'The selected image is sent to the MakeupArt cloud service for AI processing.',
                  ),
                  const _PrivacyLine(
                    icon: Icons.verified_user_outlined,
                    text: 'Only process images with the client’s permission. Named client profiles require an active consent record and a fresh operator confirmation.',
                  ),
                  const _PrivacyLine(
                    icon: Icons.phone_android_outlined,
                    text: 'The app keeps the 10 latest results in app storage. Older results are archived to Pictures/MakeupArtV8 on Android when phone storage is available.',
                  ),
                  const _PrivacyLine(
                    icon: Icons.lock_outline_rounded,
                    text: 'Cloud media follows the configured retention policy. Do not upload photos you are not authorised to process.',
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Consent revocation blocks further processing for that client. Ask the salon owner or platform administrator to handle account or data requests.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PlanRow extends StatelessWidget {
  const _PlanRow({
    required this.name,
    required this.usage,
    required this.features,
    required this.selected,
  });

  final String name;
  final String usage;
  final String features;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: selected ? theme.colorScheme.primary : theme.colorScheme.outlineVariant,
          width: selected ? 1.5 : 1,
        ),
        color: selected
            ? theme.colorScheme.primary.withValues(alpha: .08)
            : Colors.transparent,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(selected ? Icons.check_circle_rounded : Icons.circle_outlined, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: theme.textTheme.titleMedium),
                const SizedBox(height: 2),
                Text(usage, style: theme.textTheme.bodySmall),
                const SizedBox(height: 4),
                Text(features),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PrivacyLine extends StatelessWidget {
  const _PrivacyLine({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Text(text)),
        ],
      ),
    );
  }
}
