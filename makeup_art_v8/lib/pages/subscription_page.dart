import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_client.dart';
import '../widgets/license_page_button.dart';

class SubscriptionPage extends StatefulWidget {
  const SubscriptionPage({
    super.key,
    required this.api,
    required this.salonId,
    required this.subscription,
    required this.onLogout,
    required this.onRetry,
    required this.loading,
  });

  final ApiClient api;
  final String salonId;
  final Map<String, dynamic> subscription;
  final VoidCallback onLogout;
  final Future<void> Function() onRetry;
  final bool loading;

  @override
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  String _requestedPlan = 'pro';
  int _requestedDays = 365;
  bool _copyingRequest = false;

  Future<void> _copyUpgradeRequest() async {
    setState(() => _copyingRequest = true);
    try {
      var salonName = 'Salon ${widget.salonId}';
      try {
        final profile = await widget.api.getSalonProfile();
        final savedName = profile['name']?.toString().trim();
        if (savedName != null && savedName.isNotEmpty) salonName = savedName;
      } catch (_) {
        // The request can still be composed from the salon id if the profile endpoint is unavailable.
      }
      final currentPlan = widget.subscription['plan']?.toString() ?? 'unknown';
      final request = 'MakeupArt V8 plan activation request\n'
          'Salon: $salonName\n'
          'Salon ID: ${widget.salonId}\n'
          'Current plan: $currentPlan\n'
          'Requested plan: ${_requestedPlan.toUpperCase()}\n'
          'Requested term: $_requestedDays days\n'
          'Please confirm price, payment instructions and activation date.';
      await Clipboard.setData(ClipboardData(text: request));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Plan request copied. Send it to the MakeupArt platform administrator.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not copy the activation request.')),
        );
      }
    } finally {
      if (mounted) setState(() => _copyingRequest = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final end = widget.subscription['current_period_end'];
    final status = widget.subscription['status']?.toString() ?? 'inactive';
    final plan = widget.subscription['plan']?.toString() ?? 'unknown';
    final remaining = (widget.subscription['remaining'] as num?)?.toInt();
    final limit = (widget.subscription['monthly_limit'] as num?)?.toInt();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Subscription'),
        actions: [
          const LicensePageButton(),
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(
                    Icons.lock_clock_outlined,
                    size: 52,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Subscription access paused',
                    style: theme.textTheme.headlineSmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'This salon account is currently $status. AI processing is paused until the platform administrator activates or renews a plan.',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 14),
                  Text('Current plan: ${plan.toUpperCase()}', textAlign: TextAlign.center),
                  if (limit != null) ...[
                    const SizedBox(height: 5),
                    Text(
                      remaining == null
                          ? 'Usage: limit $limit AI jobs / month'
                          : 'Usage remaining: $remaining of $limit AI jobs this month',
                      textAlign: TextAlign.center,
                    ),
                  ],
                  if (end != null) ...[
                    const SizedBox(height: 5),
                    Text('Period ended: $end', textAlign: TextAlign.center),
                  ],
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: widget.loading ? null : widget.onRetry,
                    icon: widget.loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.refresh),
                    label: Text(widget.loading ? 'Checking...' : 'Check subscription again'),
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
                  Text('Choose your salon plan', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 8),
                  const _PlanLine(
                    name: 'Free',
                    details: '25 AI jobs / month · Natural makeup · Natural Finish and Warm Glow',
                  ),
                  const _PlanLine(
                    name: 'Basic',
                    details: '250 AI jobs / month · adds Soft Glam',
                  ),
                  const _PlanLine(
                    name: 'Pro',
                    details: '1,000 AI jobs / month · all current makeup presets and photo finishes',
                  ),
                  const _PlanLine(
                    name: 'Enterprise / Salon',
                    details: 'Unlimited AI jobs · for larger salon operations',
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Billing note: automated online checkout and automatic renewal are not configured yet. This request does not take payment; an administrator must confirm pricing and activate the subscription.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: _requestedPlan,
                    decoration: const InputDecoration(
                      labelText: 'Requested plan',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'basic', child: Text('Basic')),
                      DropdownMenuItem(value: 'pro', child: Text('Pro')),
                      DropdownMenuItem(value: 'enterprise', child: Text('Enterprise / Salon')),
                    ],
                    onChanged: (value) {
                      if (value != null) setState(() => _requestedPlan = value);
                    },
                  ),
                  const SizedBox(height: 12),
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment<int>(value: 30, label: Text('Monthly · 30 days')),
                      ButtonSegment<int>(value: 365, label: Text('Annual · 365 days')),
                    ],
                    selected: {_requestedDays},
                    onSelectionChanged: (values) {
                      setState(() => _requestedDays = values.first);
                    },
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: _copyingRequest ? null : _copyUpgradeRequest,
                    icon: _copyingRequest
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.copy_all_rounded),
                    label: Text(
                      _copyingRequest ? 'Preparing request...' : 'Copy plan activation request',
                    ),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: widget.loading ? null : widget.onLogout,
                    icon: const Icon(Icons.logout),
                    label: const Text('Sign out'),
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

class _PlanLine extends StatelessWidget {
  const _PlanLine({required this.name, required this.details});

  final String name;
  final String details;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.check_circle_outline_rounded, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: Theme.of(context).textTheme.titleMedium),
                Text(details),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
