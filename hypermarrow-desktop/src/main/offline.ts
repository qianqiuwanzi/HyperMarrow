/**
 * 离线模式管理
 *
 * 本地缓存 License + 签名验证，支持 72 小时离线宽限期。
 * 超过宽限期后需要联网验证。
 */

import { store } from './store';

const OFFLINE_GRACE_HOURS = 72;

export interface OfflineStatus {
  canUseOffline: boolean;
  offlineRemaining: number; // 剩余离线小时数
  lastOnlineVerify: string;
  message: string;
}

export function checkOfflineStatus(): OfflineStatus {
  const license = store.get('license');
  if (!license) {
    return {
      canUseOffline: false,
      offlineRemaining: 0,
      lastOnlineVerify: '',
      message: '未找到 License 缓存',
    };
  }

  const lastVerified = license.lastVerified ? new Date(license.lastVerified) : null;
  if (!lastVerified) {
    return {
      canUseOffline: false,
      offlineRemaining: 0,
      lastOnlineVerify: '',
      message: '未找到验证记录',
    };
  }

  const now = new Date();
  const hoursSinceVerify = (now.getTime() - lastVerified.getTime()) / (1000 * 60 * 60);
  const remaining = Math.max(0, OFFLINE_GRACE_HOURS - hoursSinceVerify);

  if (hoursSinceVerify > OFFLINE_GRACE_HOURS) {
    return {
      canUseOffline: false,
      offlineRemaining: 0,
      lastOnlineVerify: lastVerified.toISOString(),
      message: `离线宽限期已过 (${Math.round(hoursSinceVerify)}h > ${OFFLINE_GRACE_HOURS}h)，需要联网验证`,
    };
  }

  // 同时检查 License 是否已过期
  if (license.status === 'expired') {
    return {
      canUseOffline: false,
      offlineRemaining: 0,
      lastOnlineVerify: lastVerified.toISOString(),
      message: 'License 已过期',
    };
  }

  return {
    canUseOffline: true,
    offlineRemaining: Math.round(remaining),
    lastOnlineVerify: lastVerified.toISOString(),
    message: `离线模式可用，剩余 ${Math.round(remaining)} 小时`,
  };
}

export function shouldAttemptReconnect(): boolean {
  const status = checkOfflineStatus();
  // 剩余离线时间不足 12 小时时，建议联网
  return status.canUseOffline && status.offlineRemaining < 12;
}
