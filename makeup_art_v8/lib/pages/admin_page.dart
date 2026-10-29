import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/license_page_button.dart';
import '../widgets/developer_branding.dart';

class AdminPage extends StatefulWidget {
  const AdminPage({super.key, required this.api, required this.onLogout});

  final ApiClient api;
  final VoidCallback onLogout;

  @override
  State<AdminPage> createState() => _AdminPageState();
}

class _AdminPageState extends State<AdminPage> {
  List<Map<String, dynamic>> rows = [];
  List<Map<String, dynamic>> users = [];
  Map<String, dynamic>? revenueSummary;
  bool loading = true;
  String? error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final results = await Future.wait([
        widget.api.getAdminSubscriptions(),
        widget.api.getAdminUsers(),
      ]);
      rows = results[0];
      users = results[1];
      // Keep user/subscription management usable on older API deployments.
      try {
        revenueSummary = await widget.api.getAdminRevenueSummary();
      } catch (_) {
        revenueSummary = null;
      }
    } catch (exception) {
      error = 'Could not load admin data: $exception';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _activate(Map<String, dynamic> row) async {
    final id = row['salon_id'] as String;
    final plan = await showDialog<String>(
      context: context,
      builder: (context) {
        var selected = row['plan']?.toString() ?? 'basic';
        return StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: Text('Activate ${row['salon_name']?.toString() ?? 'Salon'}'),
            content: DropdownButtonFormField<String>(
              initialValue: selected,
              items: const [
                DropdownMenuItem(value: 'free', child: Text('Free')),
                DropdownMenuItem(value: 'basic', child: Text('Basic')),
                DropdownMenuItem(value: 'pro', child: Text('Pro')),
                DropdownMenuItem(value: 'enterprise', child: Text('Enterprise')),
              ],
              onChanged: (value) {
                if (value != null) setDialogState(() => selected = value);
              },
              decoration: const InputDecoration(labelText: 'Plan'),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, selected),
                child: const Text('Activate'),
              ),
            ],
          ),
        );
      },
    );

    if (plan == null) return;
    try {
      await widget.api.activateAdminSubscription(
        salonId: id,
        plan: plan,
        days: 30,
      );
      await _load();
    } catch (exception) {
      if (mounted) setState(() => error = 'Activation failed: $exception');
    }
  }

  Future<void> _suspend(Map<String, dynamic> row) async {
    try {
      await widget.api.suspendAdminSubscription(row['salon_id'] as String);
      await _load();
    } catch (exception) {
      if (mounted) setState(() => error = 'Suspension failed: $exception');
    }
  }

  Future<void> _recordPayment(Map<String, dynamic> row) async {
    final amountController = TextEditingController();
    final referenceController = TextEditingController();
    final notesController = TextEditingController();
    var plan = <String>{'basic', 'pro', 'enterprise'}.contains(row['plan'])
        ? row['plan'].toString()
        : 'basic';
    var paymentMethod = 'mobile_money';
    var periodDays = 30;
    String? dialogError;

    final receipt = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Record verified payment — ${row['salon_name'] ?? 'Salon'}'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'Use this only after you have independently confirmed the receipt. This records a manual verification; it does not charge a customer or contact a payment provider.',
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(
                  initialValue: plan,
                  decoration: const InputDecoration(labelText: 'Paid plan'),
                  items: const [
                    DropdownMenuItem(value: 'basic', child: Text('Basic')),
                    DropdownMenuItem(value: 'pro', child: Text('Pro')),
                    DropdownMenuItem(value: 'enterprise', child: Text('Enterprise')),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => plan = value);
                  },
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  initialValue: paymentMethod,
                  decoration: const InputDecoration(labelText: 'Payment method'),
                  items: const [
                    DropdownMenuItem(value: 'mobile_money', child: Text('Mobile money')),
                    DropdownMenuItem(value: 'bank_transfer', child: Text('Bank transfer')),
                    DropdownMenuItem(value: 'cash', child: Text('Cash')),
                    DropdownMenuItem(value: 'card', child: Text('Card')),
                    DropdownMenuItem(value: 'manual', child: Text('Other / manual')),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => paymentMethod = value);
                  },
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: amountController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Amount received (TZS)',
                    hintText: 'e.g. 30000.00',
                  ),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  initialValue: periodDays,
                  decoration: const InputDecoration(labelText: 'Access period'),
                  items: const [
                    DropdownMenuItem(value: 30, child: Text('30 days')),
                    DropdownMenuItem(value: 90, child: Text('90 days')),
                    DropdownMenuItem(value: 180, child: Text('180 days')),
                    DropdownMenuItem(value: 365, child: Text('365 days')),
                  ],
                  onChanged: (value) {
                    if (value != null) setDialogState(() => periodDays = value);
                  },
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: referenceController,
                  decoration: InputDecoration(
                    labelText: 'Receipt / transaction reference',
                    helperText: {'mobile_money', 'bank_transfer', 'card'}.contains(paymentMethod)
                        ? 'Required for this payment method'
                        : 'Recommended for audit and duplicate prevention',
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: notesController,
                  maxLines: 2,
                  decoration: const InputDecoration(labelText: 'Verification notes (optional)'),
                ),
                if (dialogError != null) ...[
                  const SizedBox(height: 10),
                  Text(
                    dialogError!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancel'),
            ),
            FilledButton.icon(
              icon: const Icon(Icons.verified_outlined),
              label: const Text('Record and activate'),
              onPressed: () {
                final amount = double.tryParse(amountController.text.trim());
                final needsReference = {'mobile_money', 'bank_transfer', 'card'}.contains(paymentMethod);
                if (amount == null || !amount.isFinite || amount <= 0) {
                  setDialogState(() => dialogError = 'Enter a valid amount greater than zero.');
                  return;
                }
                if (needsReference && referenceController.text.trim().isEmpty) {
                  setDialogState(() => dialogError = 'Enter the receipt or transaction reference.');
                  return;
                }
                Navigator.pop(dialogContext, {
                  'plan': plan,
                  'payment_method': paymentMethod,
                  'amount': amountController.text.trim(),
                  'period_days': periodDays,
                  'reference': referenceController.text.trim(),
                  'notes': notesController.text.trim(),
                });
              },
            ),
          ],
        ),
      ),
    );

    amountController.dispose();
    referenceController.dispose();
    notesController.dispose();
    if (receipt == null) return;

    try {
      await widget.api.recordAdminPayment(
        salonId: row['salon_id'] as String,
        plan: receipt['plan'] as String,
        amount: receipt['amount'] as String,
        currency: 'TZS',
        paymentMethod: receipt['payment_method'] as String,
        periodDays: receipt['period_days'] as int,
        reference: receipt['reference'] as String,
        notes: receipt['notes'] as String,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Verified receipt recorded and subscription activated.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      await _load();
    } catch (exception) {
      if (mounted) setState(() => error = 'Payment record failed: $exception');
    }
  }

  Future<void> _setUserStatus(Map<String, dynamic> user, bool active) async {
    final name = user['full_name']?.toString() ?? user['email']?.toString() ?? 'User';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(active ? 'Unblock user?' : 'Block user?'),
        content: Text(
          active
              ? 'Allow $name to use the app again.'
              : 'Immediately stop $name from signing in and using the app.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(active ? 'Unblock' : 'Block'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await widget.api.setAdminUserStatus(
        userId: user['id'] as String,
        active: active,
      );
      await _load();
    } catch (exception) {
      if (mounted) setState(() => error = 'User status update failed: $exception');
    }
  }

  @override
  Widget build(BuildContext context) {
    final activeUsers = users.where((user) => user['is_active'] == true).length;
    final blockedUsers = users.where((user) => user['is_active'] != true).length;
    final freeUsers = users.where((user) => user['plan'] == 'free').length;

    return Scaffold(
      appBar: AppBar(
        title: const Text('MakeupArt Admin'),
        actions: [
          const LicensePageButton(),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(18),
                children: [
                  const Align(
                    alignment: Alignment.centerRight,
                    child: DeveloperBranding(compact: true),
                  ),
                  const SizedBox(height: 8),
                  if (error != null) ...[
                    Text(
                      error!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                    const SizedBox(height: 12),
                  ],
                  Text(
                    'Project overview',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      _MetricCard(label: 'Total users', value: '${users.length}'),
                      _MetricCard(label: 'Active', value: '$activeUsers'),
                      _MetricCard(label: 'Blocked', value: '$blockedUsers'),
                      _MetricCard(label: 'Free plan', value: '$freeUsers'),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Verified payment ledger',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Records platform-admin-verified receipts only. This does not automatically charge customers or verify payments with a provider.',
                  ),
                  const SizedBox(height: 10),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: revenueSummary == null
                          ? const Text('Payment ledger is unavailable from the current API deployment.')
                          : Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Text(
                                  'Confirmed receipts this month: ${revenueSummary?['transaction_count'] ?? 0}',
                                  style: Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 8),
                                ...((revenueSummary?['totals_by_currency'] as List<dynamic>? ?? const [])
                                    .whereType<Map>()
                                    .map((total) => Padding(
                                          padding: const EdgeInsets.symmetric(vertical: 3),
                                          child: Text(
                                            '${total['currency']}: ${total['collected_total']} (${total['transaction_count']} receipt(s))',
                                          ),
                                        ))),
                                OutlinedButton.icon(
                                  onPressed: _load,
                                  icon: const Icon(Icons.refresh),
                                  label: const Text('Refresh verified payments'),
                                ),
                              ],
                            ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'Users & access',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Block or unblock individual accounts. Blocked users are denied API access immediately.',
                  ),
                  const SizedBox(height: 12),
                  if (users.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(20),
                        child: Text('No users yet.'),
                      ),
                    ),
                  ...users.map((user) {
                    final active = user['is_active'] == true;
                    final platformAdmin = user['is_platform_admin'] == true;
                    return Card(
                      margin: const EdgeInsets.only(bottom: 10),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    user['full_name']?.toString() ??
                                        user['email']?.toString() ??
                                        'User',
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                ),
                                Chip(
                                  label: Text(
                                    platformAdmin
                                        ? 'PROJECT ADMIN'
                                        : active
                                            ? 'ACTIVE'
                                            : 'BLOCKED',
                                  ),
                                ),
                              ],
                            ),
                            Text(user['email']?.toString() ?? '—'),
                            Text('Salon: ${user['salon_name']?.toString() ?? '—'}'),
                            Text('Role: ${user['role']?.toString() ?? '—'}'),
                            Text(
                              'Plan: ${user['plan']?.toString() ?? '—'} · '
                              '${user['subscription_status']?.toString() ?? '—'}',
                            ),
                            const SizedBox(height: 10),
                            if (!platformAdmin)
                              OutlinedButton.icon(
                                onPressed: () => _setUserStatus(user, !active),
                                icon: Icon(
                                  active
                                      ? Icons.block_outlined
                                      : Icons.check_circle_outline,
                                ),
                                label: Text(active ? 'Block user' : 'Unblock user'),
                              ),
                          ],
                        ),
                      ),
                    );
                  }),
                  const SizedBox(height: 24),
                  Text(
                    'Salon subscriptions',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Free plan is available without a paid renewal. Basic, Pro and Enterprise can still be activated by the project admin.',
                  ),
                  const SizedBox(height: 12),
                  if (rows.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(20),
                        child: Text('No salon subscriptions yet.'),
                      ),
                    ),
                  ...rows.map((row) {
                    final status = row['status']?.toString() ?? 'unknown';
                    final active = status == 'active' || status == 'trialing';
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    row['salon_name']?.toString() ?? 'Salon',
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                ),
                                Chip(label: Text(status)),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text('Owner: ${row['owner_email']?.toString() ?? '—'}'),
                            Text('Plan: ${row['plan']?.toString() ?? '—'}'),
                            Text(
                              'Ends: ${row['current_period_end']?.toString() ?? '—'} '
                              '(${row['days_remaining']?.toString() ?? '—'} days)',
                            ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Expanded(
                                  child: FilledButton.icon(
                                    onPressed: () => _activate(row),
                                    icon: const Icon(Icons.check_circle_outline),
                                    label: Text(active ? 'Renew / activate' : 'Activate'),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: OutlinedButton.icon(
                                    onPressed: active ? () => _suspend(row) : null,
                                    icon: const Icon(Icons.pause_circle_outline),
                                    label: const Text('Suspend'),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            OutlinedButton.icon(
                              onPressed: () => _recordPayment(row),
                              icon: const Icon(Icons.receipt_long_outlined),
                              label: const Text('Record verified payment'),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        width: 145,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label),
              const SizedBox(height: 6),
              Text(
                value,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
