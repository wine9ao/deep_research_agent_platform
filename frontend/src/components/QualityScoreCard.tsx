import React from 'react';
import { Card, Row, Col, Typography, Progress, Space, Divider, Empty } from 'antd';
import type { QualityScores } from '../api/client';

const { Title, Text } = Typography;

interface QualityScoreCardProps {
  scores: QualityScores | null;
}

const SCORE_DIMENSIONS = [
  { key: 'completeness_score', label: '完整性', icon: '📋' },
  { key: 'factuality_score', label: '事实准确性', icon: '✅' },
  { key: 'logic_score', label: '逻辑性', icon: '🧠' },
  { key: 'citation_score', label: '引用质量', icon: '📚' },
  { key: 'data_score', label: '数据充分性', icon: '📊' },
  { key: 'readability_score', label: '可读性', icon: '📖' },
] as const;

const getScoreColor = (score: number): string => {
  if (score >= 85) return '#52c41a';
  if (score >= 70) return '#faad14';
  return '#ff4d4f';
};

const getScoreStatus = (score: number): 'success' | 'normal' | 'exception' => {
  if (score >= 85) return 'success';
  if (score >= 70) return 'normal';
  return 'exception';
};

const QualityScoreCard: React.FC<QualityScoreCardProps> = ({ scores }) => {
  if (!scores) {
    return (
      <Empty
        description="暂无质量评分数据"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <div>
      {/* Overall score highlight card */}
      <Card
        style={{
          textAlign: 'center',
          borderRadius: 12,
          background: 'linear-gradient(135deg, #f0f5ff 0%, #e6f7ff 100%)',
          marginBottom: 24,
          border: '2px solid #1677ff',
        }}
      >
        <Text type="secondary" style={{ fontSize: 15 }}>
          综合评分
        </Text>
        <div style={{ margin: '12px 0' }}>
          <span
            style={{
              fontSize: 56,
              fontWeight: 800,
              color: getScoreColor((scores.final_score || 0)),
              lineHeight: 1,
            }}
          >
            {(scores.final_score || 0)}
          </span>
          <span
            style={{
              fontSize: 20,
              color: '#999',
              marginLeft: 4,
            }}
          >
            / 100
          </span>
        </div>
        <Progress
          percent={(scores.final_score || 0)}
          status={getScoreStatus((scores.final_score || 0))}
          strokeColor={getScoreColor((scores.final_score || 0))}
          showInfo={false}
          style={{ maxWidth: 300, margin: '0 auto' }}
        />
      </Card>

      {/* Dimension scores */}
      <Row gutter={[16, 16]}>
        {SCORE_DIMENSIONS.map((dim) => {
          const score = scores[dim.key as keyof QualityScores] as number;
          const color = getScoreColor(score);
          return (
            <Col xs={12} sm={8} md={4} key={dim.key}>
              <Card
                size="small"
                style={{
                  textAlign: 'center',
                  borderRadius: 10,
                  height: '100%',
                  borderTop: `3px solid ${color}`,
                }}
              >
                <div style={{ fontSize: 20, marginBottom: 4 }}>{dim.icon}</div>
                <Text strong style={{ display: 'block', fontSize: 13, marginBottom: 8 }}>
                  {dim.label}
                </Text>
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color,
                    lineHeight: 1,
                  }}
                >
                  {score}
                </div>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  分
                </Text>
                <Progress
                  percent={score}
                  strokeColor={color}
                  showInfo={false}
                  size="small"
                  style={{ marginTop: 4 }}
                />
              </Card>
            </Col>
          );
        })}
      </Row>

      {/* Comments */}
      {(scores as any).comments && (
        <>
          <Divider style={{ margin: '24px 0 16px' }} />
          <Card
            size="small"
            title="评审意见"
            style={{ borderRadius: 10, background: '#fafafa' }}
          >
            <Text style={{ fontSize: 14, lineHeight: 1.8 }}>
              {scores.comments}
            </Text>
          </Card>
        </>
      )}
    </div>
  );
};

export default QualityScoreCard;
