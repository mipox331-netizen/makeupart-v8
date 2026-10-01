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
      rows = await widget.api.getAdminSubscriptions();
    } catch (exception) {
      error = 'Could not load subscriptions: $exception';
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
              value: selected,
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
                child: const Text('Activate 30 days'),
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

  @override
  Widget build(BuildContext context) {
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
                  Text(
                    'Salon subscriptions',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Expired accounts are suspended automatically. Data is retained so the salon can be reactivated after payment.',
                  ),
                  if (error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      error!,
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ],
                  const SizedBox(height: 16),
                  if (rows.isEmpty)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(20),
                        child: Text('No salon subscriptions yet.'),
                      ),
                    ),
                  ...rows.map(
                    (row) {
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
                                'Ends: ${row['current_period_end']?.toString() ?? '—'} ' +
                                    '(${row['days_remaining']?.toString() ?? '—'} days)',
                              ),
                              const SizedBox(height: 12),
                              Row(
                                children: [
                                  Expanded(
                                    child: FilledButton.icon(
                                      onPressed: () => _activate(row),
                                      icon: const Icon(Icons.check_circle_outline),
                                      label: Text(active ? 'Renew 30d' : 'Activate 30d'),
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
                    },
                  ),
                ],
              ),
            ),
    );
  }
}
