import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../widgets/license_page_button.dart';

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
  bool loading = true;
  String? error;
  String searchQuery = '';
  String planFilter = 'all';
  String revenuePeriod = 'month';
  Map<String, dynamic> revenueSummary = const {};
  String? revenueError;

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
      try {
        revenueSummary = await widget.api.getAdminRevenueSummary(
          period: revenuePeriod,
        );
        revenueError = null;
      } catch (_) {
        revenueSummary = const {};
        revenueError =
            'Revenue summary is unavailable. Verify the backend is deployed with the payment-ledger migration.';
      }
    } catch (exception) {
      error = 'Could not load admin data: $exception';
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _recordVerifiedPayment() async {
    if (rows.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Create or register a salon before recording a payment.')),
      );
      return;
    }

    final amountController = TextEditingController();
    final referenceController = TextEditingController();
    final notesController = TextEditingController();
    try {
      final payment = await showDialog<Map<String, Object?>>(
        context: context,
        builder: (dialogContext) {
          var selectedSalon = rows.first['salon_id']?.toString() ?? '';
          var selectedPlan = 'pro';
          var selectedCurrency = 'TZS';
          var selectedMethod = 'mobile_money';
          var selectedDays = 30;
          String? formError;

          return StatefulBuilder(
            builder: (context, setDialogState) => AlertDialog(
              title: const Text('Record verified payment'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Use this only after funds have actually been received. It records the receipt and activates the selected salon plan; it does not charge the customer.',
                    ),
                    const SizedBox(height: 14),
                    DropdownButtonFormField<String>(
                      initialValue: selectedSalon,
                      decoration: const InputDecoration(
                        labelText: 'Salon',
                        border: OutlineInputBorder(),
                      ),
                      items: rows.map((row) {
                        final id = row['salon_id']?.toString() ?? '';
                        final name = row['salon_name']?.toString() ?? id;
                        return DropdownMenuItem<String>(
                          value: id,
                          child: Text(
                            name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        );
                      }).toList(),
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => selectedSalon = value);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedPlan,
                      decoration: const InputDecoration(
                        labelText: 'Plan to activate',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'basic', child: Text('Basic')),
                        DropdownMenuItem(value: 'pro', child: Text('Pro')),
                        DropdownMenuItem(value: 'enterprise', child: Text('Enterprise / Salon')),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => selectedPlan = value);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: amountController,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                        labelText: 'Amount received',
                        hintText: 'e.g. 120000',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedCurrency,
                      decoration: const InputDecoration(
                        labelText: 'Currency',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'TZS', child: Text('TZS — Tanzanian shilling')),
                        DropdownMenuItem(value: 'USD', child: Text('USD — US dollar')),
                        DropdownMenuItem(value: 'KES', child: Text('KES — Kenyan shilling')),
                        DropdownMenuItem(value: 'UGX', child: Text('UGX — Ugandan shilling')),
                        DropdownMenuItem(value: 'EUR', child: Text('EUR — euro')),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => selectedCurrency = value);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: selectedMethod,
                      decoration: const InputDecoration(
                        labelText: 'How was it received?',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'mobile_money', child: Text('Mobile money')),
                        DropdownMenuItem(value: 'bank_transfer', child: Text('Bank transfer')),
                        DropdownMenuItem(value: 'cash', child: Text('Cash')),
                        DropdownMenuItem(value: 'manual', child: Text('Other verified method')),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setDialogState(() => selectedMethod = value);
                        }
                      },
                    ),
                    const SizedBox(height: 12),
                    SegmentedButton<int>(
                      segments: const [
                        ButtonSegment<int>(value: 30, label: Text('Monthly · 30 days')),
                        ButtonSegment<int>(value: 365, label: Text('Annual · 365 days')),
                      ],
                      selected: {selectedDays},
                      onSelectionChanged: (values) {
                        setDialogState(() => selectedDays = values.first);
                      },
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: referenceController,
                      decoration: const InputDecoration(
                        labelText: 'Transaction reference (recommended)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: notesController,
                      maxLines: 2,
                      maxLength: 500,
                      decoration: const InputDecoration(
                        labelText: 'Internal note (optional)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    if (formError != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        formError!,
                        style: TextStyle(color: Theme.of(context).colorScheme.error),
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton.icon(
                  onPressed: () {
                    final amount = amountController.text.trim().replaceAll(',', '');
                    final parsed = double.tryParse(amount);
                    if (parsed == null || !parsed.isFinite || parsed <= 0) {
                      setDialogState(() => formError = 'Enter an amount greater than zero.');
                      return;
                    }
                    Navigator.of(dialogContext).pop({
                      'salon_id': selectedSalon,
                      'plan': selectedPlan,
                      'amount': amount,
                      'currency': selectedCurrency,
                      'payment_method': selectedMethod,
                      'period_days': selectedDays,
                    });
                  },
                  icon: const Icon(Icons.verified_rounded),
                  label: const Text('Record & activate'),
                ),
              ],
            ),
          );
        },
      );

      if (payment == null || !mounted) return;
      setState(() {
        loading = true;
        error = null;
      });
      await widget.api.recordAdminPayment(
        salonId: payment['salon_id']! as String,
        plan: payment['plan']! as String,
        amount: payment['amount']! as String,
        currency: payment['currency']! as String,
        paymentMethod: payment['payment_method']! as String,
        periodDays: payment['period_days']! as int,
        reference: referenceController.text,
        notes: notesController.text,
      );
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Verified payment recorded and subscription activated.'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (exception) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Payment was not recorded: $exception'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    } finally {
      amountController.dispose();
      referenceController.dispose();
      notesController.dispose();
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _activate(Map<String, dynamic> row) async {
    final id = row['salon_id'] as String;
    final selection = await showDialog<Map<String, Object>>(
      context: context,
      builder: (context) {
        var selectedPlan = row['plan']?.toString() ?? 'basic';
        var selectedDays = 30;
        return StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: Text('Activate ${row['salon_name']?.toString() ?? 'Salon'}'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: selectedPlan,
                    items: const [
                      DropdownMenuItem(value: 'free', child: Text('Free')),
                      DropdownMenuItem(value: 'basic', child: Text('Basic')),
                      DropdownMenuItem(value: 'pro', child: Text('Pro')),
                      DropdownMenuItem(value: 'enterprise', child: Text('Enterprise / Salon')),
                    ],
                    onChanged: (value) {
                      if (value != null) setDialogState(() => selectedPlan = value);
                    },
                    decoration: const InputDecoration(labelText: 'Plan'),
                  ),
                  const SizedBox(height: 16),
                  const Text('Paid access term'),
                  const SizedBox(height: 8),
                  SegmentedButton<int>(
                    segments: const [
                      ButtonSegment<int>(value: 30, label: Text('Monthly · 30 days')),
                      ButtonSegment<int>(value: 365, label: Text('Annual · 365 days')),
                    ],
                    selected: {selectedDays},
                    onSelectionChanged: (values) =>
                        setDialogState(() => selectedDays = values.first),
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'This sets the access period only. Verify payment separately; this admin action does not charge the customer.',
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(
                  context,
                  {'plan': selectedPlan, 'days': selectedDays},
                ),
                child: const Text('Activate'),
              ),
            ],
          ),
        );
      },
    );

    if (selection == null) return;
    try {
      await widget.api.activateAdminSubscription(
        salonId: id,
        plan: selection['plan'] as String,
        days: selection['days'] as int,
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
    final paidSalons = rows.where((row) =>
        row['plan'] != 'free' &&
        (row['status'] == 'active' || row['status'] == 'trialing')).length;
    final expiringSoon = rows.where((row) {
      final days = (row['days_remaining'] as num?)?.toInt();
      return days != null &&
          days <= 7 &&
          (row['status'] == 'active' || row['status'] == 'trialing');
    }).length;
    final query = searchQuery.trim().toLowerCase();
    final filteredUsers = users.where((user) {
      final text = [
        user['full_name'],
        user['email'],
        user['salon_name'],
        user['role'],
        user['plan'],
        user['subscription_status'],
      ].map((value) => value?.toString().toLowerCase() ?? '').join(' ');
      final matchesQuery = query.isEmpty || text.contains(query);
      final matchesPlan = planFilter == 'all' || user['plan'] == planFilter;
      return matchesQuery && matchesPlan;
    }).toList();
    final filteredRows = rows.where((row) {
      final text = [
        row['salon_name'],
        row['owner_email'],
        row['plan'],
        row['status'],
      ].map((value) => value?.toString().toLowerCase() ?? '').join(' ');
      final matchesQuery = query.isEmpty || text.contains(query);
      final matchesPlan = planFilter == 'all' || row['plan'] == planFilter;
      return matchesQuery && matchesPlan;
    }).toList();

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
                      _MetricCard(label: 'Active paid plans', value: '$paidSalons'),
                      const _MetricCard(label: 'Revenue', value: 'Verified ledger'),
                      _MetricCard(label: 'Due in 7 days', value: '$expiringSoon'),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.account_balance_wallet_outlined, size: 24),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Verified payments & revenue',
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          const Text(
                            'Amounts below are receipts an administrator manually confirmed. Recording a receipt activates the plan but never sends a charge to a payment provider. Automatic renewals are not connected.',
                          ),
                          const SizedBox(height: 12),
                          SegmentedButton<String>(
                            segments: const [
                              ButtonSegment<String>(value: 'month', label: Text('This month')),
                              ButtonSegment<String>(value: 'year', label: Text('This year')),
                            ],
                            selected: {revenuePeriod},
                            onSelectionChanged: (values) {
                              final next = values.first;
                              if (next != revenuePeriod) {
                                setState(() {
                                  revenuePeriod = next;
                                  loading = true;
                                });
                                _load();
                              }
                            },
                          ),
                          const SizedBox(height: 12),
                          if (revenueError != null)
                            Text(
                              revenueError!,
                              style: TextStyle(color: Theme.of(context).colorScheme.error),
                            ),
                          if (revenueError == null && revenueSummary.isNotEmpty) ...[
                            Text(
                              '${revenueSummary['transaction_count'] ?? 0} verified receipts in selected period',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 8),
                            if ((revenueSummary['totals_by_currency'] as List<dynamic>? ?? const []).isEmpty)
                              const Text('No verified payments recorded for this period.')
                            else
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: ((revenueSummary['totals_by_currency'] as List<dynamic>? ?? const [])
                                    .map((item) => Map<String, dynamic>.from(item as Map)))
                                    .map((item) {
                                  final currency = item['currency']?.toString() ?? '';
                                  final total = double.tryParse(item['collected_total']?.toString() ?? '') ?? 0;
                                  return _MetricCard(
                                    label: '$currency collected',
                                    value: total.toStringAsFixed(2),
                                  );
                                }).toList(),
                              ),
                            const SizedBox(height: 12),
                            if ((revenueSummary['recent_payments'] as List<dynamic>? ?? const []).isNotEmpty)
                              ...((revenueSummary['recent_payments'] as List<dynamic>? ?? const [])
                                  .take(8)
                                  .map((item) => Map<String, dynamic>.from(item as Map)))
                                  .map((payment) => ListTile(
                                        contentPadding: EdgeInsets.zero,
                                        leading: const Icon(Icons.receipt_long_outlined),
                                        title: Text(
                                          payment['salon_name']?.toString() ?? 'Salon',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        subtitle: Text(
                                          '${payment['plan']?.toString().toUpperCase() ?? 'PLAN'} · ${payment['payment_method'] ?? 'manual'} · ${payment['reference'] ?? 'No reference'}',
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                        trailing: Text(
                                          '${payment['currency'] ?? ''} ${(double.tryParse(payment['amount']?.toString() ?? '') ?? 0).toStringAsFixed(2)}',
                                          textAlign: TextAlign.end,
                                        ),
                                      )),
                          ],
                          const SizedBox(height: 14),
                          FilledButton.icon(
                            onPressed: loading ? null : _recordVerifiedPayment,
                            icon: const Icon(Icons.add_card_rounded),
                            label: const Text('Record verified payment & activate plan'),
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
                  const SizedBox(height: 10),
                  TextField(
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search_rounded),
                      labelText: 'Search users, salons, plans or status',
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (value) => setState(() => searchQuery = value),
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<String>(
                    initialValue: planFilter,
                    decoration: const InputDecoration(
                      labelText: 'Filter by plan',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'all', child: Text('All plans')),
                      DropdownMenuItem(value: 'free', child: Text('Free')),
                      DropdownMenuItem(value: 'basic', child: Text('Basic')),
                      DropdownMenuItem(value: 'pro', child: Text('Pro')),
                      DropdownMenuItem(value: 'enterprise', child: Text('Enterprise / Salon')),
                    ],
                    onChanged: (value) {
                      if (value != null) setState(() => planFilter = value);
                    },
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Block or unblock individual accounts. Blocked users are denied API access immediately.',
                  ),
                  const SizedBox(height: 12),
                  if (filteredUsers.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Text(users.isEmpty ? 'No users yet.' : 'No users match this filter.'),
                      ),
                    ),
                  ...filteredUsers.map((user) {
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
                    'Free is available without renewal. Basic, Pro and Enterprise can be activated monthly (30 days) or annually (365 days) by the platform administrator. Payment confirmation remains a separate step until a billing provider is connected.',
                  ),
                  const SizedBox(height: 12),
                  if (filteredRows.isEmpty)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(20),
                        child: Text(rows.isEmpty ? 'No salon subscriptions yet.' : 'No subscriptions match this filter.'),
                      ),
                    ),
                  ...filteredRows.map((row) {
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
