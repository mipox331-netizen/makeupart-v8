import 'dart:io';

import 'package:flutter/material.dart';

import '../services/favorite_image_store.dart';

class FavoritesPage extends StatefulWidget {
  const FavoritesPage({super.key, required this.salonId});

  final String salonId;

  @override
  State<FavoritesPage> createState() => _FavoritesPageState();
}

class _FavoritesPageState extends State<FavoritesPage> {
  late final FavoriteImageStore _store;
  List<File> _files = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _store = FavoriteImageStore(scope: widget.salonId);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final files = await _store.list();
      if (mounted) setState(() => _files = files);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not load favorites stored on this device.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _remove(File file) async {
    try {
      final jobId = file.uri.pathSegments.last
          .replaceFirst(RegExp(r'^favorite_'), '')
          .replaceFirst(RegExp(r'\.png$', caseSensitive: false), '');
      await _store.remove(jobId);
      if (mounted) {
        setState(() => _files.removeWhere((item) => item.path == file.path));
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Removed from favorites.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not remove this favorite.')),
        );
      }
    }
  }

  Future<void> _preview(File file) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => Dialog(
        insetPadding: const EdgeInsets.all(18),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(
                child: InteractiveViewer(
                  child: Image.file(
                    file,
                    fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => const Icon(
                      Icons.broken_image_outlined,
                      size: 48,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () {
                        Navigator.of(dialogContext).pop();
                        _remove(file);
                      },
                      icon: const Icon(Icons.favorite_border_rounded),
                      label: const Text('Remove'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: () => Navigator.of(dialogContext).pop(),
                      child: const Text('Done'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Favorite results'),
        actions: [
          IconButton(
            tooltip: 'Refresh favorites',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        FilledButton.icon(
                          onPressed: _load,
                          icon: const Icon(Icons.refresh_rounded),
                          label: const Text('Try again'),
                        ),
                      ],
                    ),
                  ),
                )
              : _files.isEmpty
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.favorite_border_rounded, size: 58),
                            const SizedBox(height: 12),
                            Text(
                              'No favorites yet',
                              style: theme.textTheme.titleLarge,
                            ),
                            const SizedBox(height: 6),
                            const Text(
                              'Save a finished beauty result as a favorite to keep it on this device.',
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: GridView.builder(
                        padding: const EdgeInsets.all(16),
                        physics: const AlwaysScrollableScrollPhysics(),
                        gridDelegate:
                            const SliverGridDelegateWithFixedCrossAxisCount(
                          crossAxisCount: 2,
                          crossAxisSpacing: 12,
                          mainAxisSpacing: 12,
                          childAspectRatio: .72,
                        ),
                        itemCount: _files.length,
                        itemBuilder: (context, index) {
                          final file = _files[index];
                          return Card(
                            clipBehavior: Clip.antiAlias,
                            child: Stack(
                              fit: StackFit.expand,
                              children: [
                                InkWell(
                                  onTap: () => _preview(file),
                                  child: Image.file(
                                    file,
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, __, ___) => const Center(
                                      child: Icon(Icons.broken_image_outlined),
                                    ),
                                  ),
                                ),
                                Positioned(
                                  right: 8,
                                  top: 8,
                                  child: Material(
                                    color: Colors.black.withValues(alpha: .65),
                                    shape: const CircleBorder(),
                                    child: IconButton(
                                      tooltip: 'Remove from favorites',
                                      onPressed: () => _remove(file),
                                      icon: const Icon(
                                        Icons.favorite_rounded,
                                        color: Colors.pinkAccent,
                                      ),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
