import 'package:flutter/material.dart';

import '../widgets/developer_branding.dart';
import '../widgets/license_page_button.dart';

class SubscriptionPage extends StatefulWidget {
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
  State<SubscriptionPage> createState() => _SubscriptionPageState();
}

class _SubscriptionPageState extends State<SubscriptionPage> {
  static const _providers = <String, String>{
    'vodacom': 'Vodacom M-Pesa',
    'tigo': 'Tigo Pesa',
    'airtel': 'Airtel Money',
  };

  String selectedProvider = 'vodacom';

  @override
  Widget build(BuildContext context) {
    final end = widget.subscription['current_period_end'];
    final status = widget.subscription['status']?.toString() ?? 'inactive';
    final plan = widget.subscription['plan']?.toString() ?? 'unknown';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Subscription'),
        actions: [
          const LicensePageButton(),
          IconButton(onPressed: widget.onLogout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
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
                        const Divider(),
                        Text(
                          'Pay with mobile money',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'Choose the network you normally use in Tanzania.',
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            for (final provider in _providers.entries)
                              ChoiceChip(
                                key: ValueKey('mobile-money-${provider.key}'),
                                avatar: Icon(
                                  selectedProvider == provider.key
                                      ? Icons.radio_button_checked
                                      : Icons.radio_button_unchecked,
                                  size: 18,
                                ),
                                label: Text(provider.value),
                                selected: selectedProvider == provider.key,
                                onSelected: widget.loading
                                    ? null
                                    : (_) => setState(
                                          () => selectedProvider = provider.key,
                                        ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          'Selected: ${_providers[selectedProvider]}',
                          key: const ValueKey('selected-mobile-money-provider'),
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                              ),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.surfaceContainerLow,
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: const Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(Icons.info_outline_rounded),
                              SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  'Network selection is ready, but automatic mobile-money collection is not connected yet. Do not send money to an unverified number. Payment instructions and subscription activation will be enabled after the official merchant gateway is configured.',
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 22),
                        FilledButton.icon(
                          onPressed: widget.loading ? null : widget.onRetry,
                          icon: widget.loading
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.refresh),
                          label: Text(
                            widget.loading ? 'Checking...' : 'Check subscription again',
                          ),
                        ),
                        const SizedBox(height: 10),
                        OutlinedButton.icon(
                          onPressed: widget.loading ? null : widget.onLogout,
                          icon: const Icon(Icons.logout),
                          label: const Text('Sign out'),
                        ),
                        const SizedBox(height: 18),
                        const DeveloperBranding(centered: true),
                      ],
                    ),
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
