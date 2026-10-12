import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../services/api_client.dart';

class BrandingSettingsPage extends StatefulWidget {
  const BrandingSettingsPage({super.key, required this.api});

  final ApiClient api;

  @override
  State<BrandingSettingsPage> createState() => _BrandingSettingsPageState();
}

class _BrandingSettingsPageState extends State<BrandingSettingsPage> {
  final ImagePicker _picker = ImagePicker();
  final _positions = const <String, String>{
    'bottom-right': 'Bottom right',
    'bottom-left': 'Bottom left',
    'top-right': 'Top right',
    'top-left': 'Top left',
  };

  Uint8List? _logoBytes;
  String _position = 'bottom-right';
  double _opacity = 0.72;
  double _size = 20;
  bool _showPhone = false;
  bool _showInstagram = false;
  bool _showTikTok = false;
  bool _loading = true;
  bool _busy = false;
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
      final data = await widget.api.getWatermarkSettings();
      Uint8List? logo;
      if (data['logo_url'] != null) {
        try {
          logo = await widget.api.fetchImage('/watermarks/me/logo');
        } catch (_) {
          // A stale logo URL must not prevent the settings screen from opening.
        }
      }
      if (!mounted) return;
      setState(() {
        _position = _positions.containsKey(data['position'])
            ? data['position'] as String
            : 'bottom-right';
        _opacity = ((data['opacity'] as num?)?.toDouble() ?? 0.72)
            .clamp(0.0, 1.0).toDouble();
        _size = ((data['size'] as num?)?.toDouble() ?? 20)
            .clamp(8.0, 48.0).toDouble();
        _showPhone = data['phone'] == true;
        _showInstagram = data['instagram'] == true;
        _showTikTok = data['tiktok'] == true;
        _logoBytes = logo;
      });
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not load branding settings. Check your connection and account permissions.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickLogo() async {
    final file = await _picker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 100,
    );
    if (file == null || !mounted) return;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.uploadWatermarkLogo(file);
      final bytes = await widget.api.fetchImage('/watermarks/me/logo');
      if (!mounted) return;
      setState(() {
        _logoBytes = bytes;
      });
      _message('Salon logo uploaded. New AI results will include it.');
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Logo upload failed. Use a valid PNG, JPEG, or WebP image under 5 MB.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _removeLogo() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.deleteWatermarkLogo();
      if (!mounted) return;
      setState(() => _logoBytes = null);
      _message('Salon logo removed. The salon name watermark stays required.');
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not remove the salon logo.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _save() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.api.updateWatermarkSettings(
        position: _position,
        opacity: _opacity,
        size: _size.round(),
        showPhone: _showPhone,
        showInstagram: _showInstagram,
        showTikTok: _showTikTok,
      );
      if (!mounted) return;
      _message('Branding settings saved for this salon.');
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not save settings. Only salon owners/admins can change branding.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(text), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Salon branding'),
        actions: [
          IconButton(
            onPressed: _busy || _loading ? null : _load,
            tooltip: 'Refresh settings',
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 28),
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFF38234E), Color(0xFF171B2B)],
                    ),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: Colors.white.withValues(alpha: .10)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.auto_awesome_rounded, size: 30),
                      const SizedBox(height: 12),
                      Text(
                        'Your brand. On every result.',
                        style: theme.textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Set how your salon is credited on AI beauty images. These settings are saved to your salon account.',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: Colors.white.withValues(alpha: .78),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Salon logo', style: theme.textTheme.titleLarge),
                        const SizedBox(height: 6),
                        const Text(
                          'Upload a transparent PNG for the cleanest result. JPEG and WebP are also accepted (maximum 5 MB).',
                        ),
                        const SizedBox(height: 16),
                        Container(
                          height: 150,
                          width: double.infinity,
                          decoration: BoxDecoration(
                            color: const Color(0xFF10131D),
                            borderRadius: BorderRadius.circular(18),
                            border: Border.all(
                              color: theme.colorScheme.outlineVariant,
                            ),
                          ),
                          child: _logoBytes == null
                              ? const Column(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Icon(Icons.add_photo_alternate_outlined,
                                        size: 38),
                                    SizedBox(height: 8),
                                    Text('No logo uploaded'),
                                  ],
                                )
                              : Padding(
                                  padding: const EdgeInsets.all(14),
                                  child: Image.memory(
                                    _logoBytes!,
                                    fit: BoxFit.contain,
                                    errorBuilder: (_, __, ___) => const Icon(
                                      Icons.broken_image_outlined,
                                      size: 40,
                                    ),
                                  ),
                                ),
                        ),
                        const SizedBox(height: 12),
                        Row(
                          children: [
                            Expanded(
                              child: FilledButton.icon(
                                onPressed: _busy ? null : _pickLogo,
                                icon: const Icon(Icons.upload_rounded),
                                label: Text(
                                  _logoBytes == null ? 'Upload logo' : 'Replace logo',
                                ),
                              ),
                            ),
                            if (_logoBytes != null) ...[
                              const SizedBox(width: 10),
                              OutlinedButton(
                                onPressed: _busy ? null : _removeLogo,
                                child: const Icon(Icons.delete_outline_rounded),
                              ),
                            ],
                          ],
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
                        Text('Watermark layout',
                            style: theme.textTheme.titleLarge),
                        const SizedBox(height: 6),
                        const Text(
                          'The salon name stays on. Choose where it appears and how strong the watermark looks.',
                        ),
                        const SizedBox(height: 16),
                        DropdownButtonFormField<String>(
                          initialValue: _position,
                          decoration: const InputDecoration(
                            labelText: 'Position on image',
                            prefixIcon: Icon(Icons.layers_outlined),
                            border: OutlineInputBorder(),
                          ),
                          items: _positions.entries
                              .map((entry) => DropdownMenuItem<String>(
                                    value: entry.key,
                                    child: Text(entry.value),
                                  ))
                              .toList(),
                          onChanged: _busy
                              ? null
                              : (value) {
                                  if (value != null) {
                                    setState(() => _position = value);
                                  }
                                },
                        ),
                        const SizedBox(height: 18),
                        Row(
                          children: [
                            const Expanded(child: Text('Watermark opacity')),
                            Text('${(_opacity * 100).round()}%'),
                          ],
                        ),
                        Slider(
                          value: _opacity,
                          min: 0.15,
                          max: 1,
                          divisions: 17,
                          onChanged: _busy
                              ? null
                              : (value) => setState(() => _opacity = value),
                        ),
                        Row(
                          children: [
                            const Expanded(child: Text('Logo / text size')),
                            Text('${_size.round()}%'),
                          ],
                        ),
                        Slider(
                          value: _size,
                          min: 8,
                          max: 48,
                          divisions: 20,
                          onChanged: _busy
                              ? null
                              : (value) => setState(() => _size = value),
                        ),
                        const Divider(height: 28),
                        Text('Extra salon details',
                            style: theme.textTheme.titleMedium),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Phone number'),
                          subtitle: const Text(
                              'Uses the phone saved in your salon profile.'),
                          value: _showPhone,
                          onChanged: _busy
                              ? null
                              : (value) => setState(() => _showPhone = value),
                        ),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Instagram handle'),
                          value: _showInstagram,
                          onChanged: _busy
                              ? null
                              : (value) =>
                                  setState(() => _showInstagram = value),
                        ),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('TikTok handle'),
                          value: _showTikTok,
                          onChanged: _busy
                              ? null
                              : (value) => setState(() => _showTikTok = value),
                        ),
                      ],
                    ),
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                ],
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: _busy ? null : _save,
                  icon: _busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_rounded),
                  label: Text(_busy ? 'Saving...' : 'Save branding settings'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Changes apply to new AI results after saving. Existing images are not modified.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
    );
  }
}
