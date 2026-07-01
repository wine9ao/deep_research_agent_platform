import React from 'react';
import { List, Typography, Tag, Space, Empty, Tooltip } from 'antd';
import {
  LinkOutlined,
  FileTextOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import type { Source } from '../api/client';

const { Text, Paragraph } = Typography;

interface SourceListProps {
  sources: Source[];
}

const SourceList: React.FC<SourceListProps> = ({ sources }) => {
  if (!sources || sources.length === 0) {
    return (
      <Empty
        description="暂无引用来源"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <List
      dataSource={sources}
      renderItem={(source: Source, index: number) => (
        <List.Item
          key={index}
          style={{
            padding: '16px 20px',
            borderRadius: 8,
            background: '#fafafa',
            marginBottom: 8,
            border: '1px solid #f0f0f0',
            transition: 'all 0.2s ease',
            cursor: source.url ? 'pointer' : 'default',
          }}
          onClick={() => {
            if (source.url) {
              window.open(source.url, '_blank', 'noopener,noreferrer');
            }
          }}
        >
          <List.Item.Meta
            avatar={
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: '#e6f4ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#1677ff',
                  fontSize: 16,
                  fontWeight: 700,
                }}
              >
                {index + 1}
              </div>
            }
            title={
              <Space size={8} wrap>
                <Text strong style={{ fontSize: 15 }}>
                  {source.title || '未命名来源'}
                </Text>
                {source.url && (
                  <Tooltip title="在新标签页打开">
                    <LinkOutlined
                      style={{ color: '#1677ff', fontSize: 12, cursor: 'pointer' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (source.url) {
                          window.open(source.url, '_blank', 'noopener,noreferrer');
                        }
                      }}
                    />
                  </Tooltip>
                )}
              </Space>
            }
            description={
              <Space size={12} wrap style={{ marginTop: 4 }}>
                <Tag icon={<FileTextOutlined />} color="blue">
                  {source.source || '未知来源'}
                </Tag>
                {source.publish_time && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    {source.publish_time}
                  </Text>
                )}
              </Space>
            }
          />
        </List.Item>
      )}
    />
  );
};

export default SourceList;
