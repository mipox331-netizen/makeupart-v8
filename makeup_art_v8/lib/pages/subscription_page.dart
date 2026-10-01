import 'package:flutter/material.dart';

class SubscriptionPage extends StatelessWidget {
  const SubscriptionPage({
    super.key,
    required this.subscription,
    required this.onLogout,
    required this.onRetry,
    required this.loading,
  });

  final Map<String, dynamic> subscription;
  final VoidCallback onLogout;
  final Future<void> Function() onRetry;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    final end = subscription['current_period_end'];
    final status = subscription['status']?.toString() ?? 'inactive';
    final plan = subscription['plan']?.toString() ?? 'unknown';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Subscription'),
        actions: [
          IconButton(onPressed: onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Icon(
                      Icons.lock_clock_outlined,
                      size: 56,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Subscription inactive',
                      style: Theme.of(context).textTheme.headlineSmall,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'This salon account is currently $status. AI processing and salon operations are paused until the subscription is renewed.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 18),
                    Text(
                      'Plan: ${plan.toUpperCase()}',
                      textAlign: TextAlign.center,
                    ),
                    if (end != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Period ended: $end',
                        textAlign: TextAlign.center,
                      ),
                    ],
                    const SizedBox(height: 22),
                    FilledButton.icon(
                      onPressed: loading ? null : onRetry,
                      icon: loading
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.refresh),
                      label: Text(loading ? 'Checking...' : 'Check subscription again'),
                    ),
                    const SizedBox(height: 10),
                    OutlinedButton.icon(
                      onPressed: loading ? null : onLogout,
                      icon: const Icon(Icons.logout),
                      label: const Text('Sign out'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
