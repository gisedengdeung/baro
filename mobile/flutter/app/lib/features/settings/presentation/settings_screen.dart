import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_exception.dart';
import '../../mobile_device/repositories/mobile_device_repository.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _tokenController = TextEditingController();
  final _edgeScopeController = TextEditingController(text: 'edge-default');
  String _platform = defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';
  bool _submitting = false;

  @override
  void dispose() {
    _tokenController.dispose();
    _edgeScopeController.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    final token = _tokenController.text.trim();
    if (token.length < 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('fcm_token은 10자 이상이어야 합니다.')),
      );
      return;
    }

    final edgeScope = _edgeScopeController.text
        .split(',')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();

    setState(() => _submitting = true);
    try {
      await ref.read(mobileDeviceRepositoryProvider).registerDevice(
            platform: _platform,
            fcmToken: token,
            edgeScope: edgeScope,
          );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('디바이스 등록 완료')),
      );
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.message)),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            '임시 방식: 수동 fcm_token 등록',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _platform,
            decoration: const InputDecoration(labelText: 'Platform'),
            items: const [
              DropdownMenuItem(value: 'android', child: Text('android')),
              DropdownMenuItem(value: 'ios', child: Text('ios')),
            ],
            onChanged: (value) {
              if (value != null) {
                setState(() => _platform = value);
              }
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _tokenController,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(
              labelText: 'fcm_token',
              hintText: '수동 토큰 값을 붙여넣으세요',
            ),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _edgeScopeController,
            decoration: const InputDecoration(
              labelText: 'edge_scope (comma separated)',
              hintText: 'edge-default,edge-a',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _submitting ? null : _register,
            child: _submitting
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('디바이스 등록'),
          ),
        ],
      ),
    );
  }
}
