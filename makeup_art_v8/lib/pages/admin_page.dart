import 'package:flutter/material.dart';

import '../services/api_client.dart';

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
      rows = results[0] as List<Map<String, dynamic>>;
      users = results[1] as List<Map<String, dynamic>>;
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
                      _MetricCard(label: 'Active', value: '${activeUsers}'),
                      _MetricCard(label: 'Blocked', value: '${blockedUsers}'),
                      _MetricCard(label: 'Free plan', value: '${freeUsers}'),
                    ],
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
