import React, { useRef, useEffect } from 'react';
import { Timeline, Typography, Tag, Space, Empty } from 'antd';
import {
  InfoCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  BugOutlined,
} from '@ant-design/icons';
import type { LogEntry } from '../api/client';

const { Text } = Typography;

interface LogViewerProps {
  logs: LogEntry[];
}

const LEVEL_CONFIG: Record<
  string,
  { color: string; icon: React.ReactNode; label: string }
> = {
  info: {
    color: 'blue',
    icon: <InfoCircleOutlined />,
    label: '信息',
  },
  warning: {
    color: 'orange',
    icon: <WarningOutlined />,
    label: '警告',
  },
  error: {
    color: 'red',
    icon: <CloseCircleOutlined />,
    label: '错误',
  },
  debug: {
    color: 'purple',
    icon: <BugOutlined />,
    label: '调试',
  },
};

const formatTimestamp = (ts: string) => {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return ts;
  }
};

const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!logs || logs.length === 0) {
    return (
      <Empty
        description="暂无执行日志"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div
      style={{
        maxHeight: 480,
        overflowY: 'auto',
        padding: '4px 0',
      }}
    >
      <Timeline
        items={logs.map((log, index) => {
          const config = LEVEL_CONFIG[log.level] || LEVEL_CONFIG.info;
          return {
            color: config.color,
            dot: config.icon,
            children: (
              <div key={index} className="log-entry-enter">
                <Space size={8} wrap style={{ marginBottom: 2 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {formatTimestamp(log.timestamp)}
                  </Text>
                  <Tag color="geekblue" style={{ fontSize: 11 }}>
                    {log.agent}
                  </Tag>
                  <Tag style={{ fontSize: 11 }}>{log.action}</Tag>
                  <Tag
                    color={config.color}
                    icon={config.icon}
                    style={{ fontSize: 11 }}
                  >
                    {config.label}
                  </Tag>
                </Space>
                <div style={{ marginTop: 4 }}>
                  <Text style={{ fontSize: 13, color: '#555' }}>
                    {log.details}
                  </Text>
                </div>
              </div>
            ),
          };
        })}
      />
      <div ref={bottomRef} />
    </div>
  );
};

export default LogViewer;
