import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Upload,
  Table,
  Input,
  List,
  Button,
  Space,
  Typography,
  Tag,
  message,
  Spin,
  Empty,
} from 'antd';
import {
  InboxOutlined,
  SearchOutlined,
  FileTextOutlined,
  DeleteOutlined,
  UploadOutlined,
  ReloadOutlined,
  BookOutlined,
} from '@ant-design/icons';
import type { UploadProps } from 'antd';
import {
  uploadDocument,
  listDocuments,
  searchKnowledge,
  DocumentItem,
  SearchResult,
} from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { Dragger } = Upload;
const { Search } = Input;

const KnowledgeBase: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [docLoading, setDocLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const fetchDocuments = useCallback(async () => {
    setDocLoading(true);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : '获取文档列表失败';
      message.error(errorMessage);
    } finally {
      setDocLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError, onProgress } = options;
    setUploading(true);
    try {
      const res = await uploadDocument(file as File, onProgress
        ? (e) => {
            if (e.total) {
              onProgress({ percent: (e.loaded / e.total) * 100 });
            }
          }
        : undefined);
      if (onSuccess) onSuccess(res, file as unknown as XMLHttpRequest);
      message.success(`文件 "${(file as File).name}" 上传成功`);
      fetchDocuments();
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : '上传失败';
      if (onError) onError(new Error(errorMessage));
      message.error(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (value: string) => {
    if (!value.trim()) {
      message.warning('请输入搜索关键词');
      return;
    }
    setSearchLoading(true);
    try {
      const results = await searchKnowledge(value.trim());
      setSearchResults(results);
      if (results.length === 0) {
        message.info('未找到相关结果');
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : '搜索失败';
      message.error(errorMessage);
    } finally {
      setSearchLoading(false);
    }
  };

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (text: string) => (
        <Space>
          <FileTextOutlined />
          <Text>{text}</Text>
        </Space>
      ),
    },
    {
      title: '文件类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 100,
      render: (t: string) => <Tag>{t.toUpperCase()}</Tag>,
    },
    {
      title: '文件大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 120,
      render: (size: number) => {
        if (!size) return '-';
        if (size < 1024) return `${size} B`;
        if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
        return `${(size / (1024 * 1024)).toFixed(1)} MB`;
      },
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      width: 180,
    },
  ];

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <BookOutlined style={{ marginRight: 8 }} />
        知识库管理
      </Title>

      <Card
        title={
          <Space>
            <UploadOutlined />
            <span>上传文档</span>
          </Space>
        }
        style={{ borderRadius: 12, marginBottom: 24 }}
      >
        <Dragger
          multiple
          accept=".txt,.md,.csv,.pdf,.docx,.json"
          customRequest={handleUpload}
          showUploadList={false}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            {uploading ? '正在上传...' : '点击或拖拽文件到此区域上传'}
          </p>
          <p className="ant-upload-hint">
            支持 TXT、Markdown、CSV、PDF、DOCX、JSON 格式文件
          </p>
        </Dragger>
      </Card>

      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>文档列表</span>
          </Space>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchDocuments}
            loading={docLoading}
            size="small"
          >
            刷新
          </Button>
        }
        style={{ borderRadius: 12, marginBottom: 24 }}
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={docLoading}
          locale={{ emptyText: <Empty description="暂无文档，请上传" /> }}
          pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `共 ${total} 个文档` }}
        />
      </Card>

      <Card
        title={
          <Space>
            <SearchOutlined />
            <span>知识检索</span>
          </Space>
        }
        style={{ borderRadius: 12 }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Search
            placeholder="输入关键词搜索知识库..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onSearch={handleSearch}
            enterButton={
              <Button type="primary" loading={searchLoading} icon={<SearchOutlined />}>
                搜索
              </Button>
            }
            size="large"
            allowClear
          />

          {searchLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin tip="正在检索..." />
            </div>
          ) : searchResults.length > 0 ? (
            <List
              dataSource={searchResults}
              renderItem={(item: SearchResult, index: number) => (
                <List.Item
                  key={index}
                  style={{
                    padding: '16px 20px',
                    borderRadius: 8,
                    background: '#fafafa',
                    marginBottom: 8,
                  }}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <Tag color="blue">相关度: {(item.score * 100).toFixed(0)}%</Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          来源: {item.source}
                        </Text>
                      </Space>
                    }
                    description={
                      <Paragraph
                        ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                        style={{ marginBottom: 0 }}
                      >
                        {item.content}
                      </Paragraph>
                    }
                  />
                </List.Item>
              )}
            />
          ) : searchQuery ? (
            <Empty description="未找到匹配结果" />
          ) : (
            <Empty description="输入关键词开始搜索知识库" />
          )}
        </Space>
      </Card>
    </div>
  );
};

export default KnowledgeBase;
