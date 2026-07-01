import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
  SearchOutlined,
  BookOutlined,
  HomeOutlined,
} from '@ant-design/icons';
import Home from './pages/Home';
import ResearchProgress from './pages/ResearchProgress';
import ReportResult from './pages/ReportResult';
import KnowledgeBase from './pages/KnowledgeBase';

const { Header, Content } = Layout;
const { Text } = Typography;

const NAV_ITEMS = [
  { key: '/', icon: <HomeOutlined />, label: <Link to="/">首页</Link> },
  {
    key: '/knowledge',
    icon: <BookOutlined />,
    label: <Link to="/knowledge">知识库</Link>,
  },
];

const App: React.FC = () => {
  const location = useLocation();

  const selectedKey =
    location.pathname === '/' ? '/' : '/' + location.pathname.split('/')[1];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: '#001529',
          position: 'sticky',
          top: 0,
          zIndex: 100,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <SearchOutlined style={{ fontSize: 24, color: '#1677ff' }} />
          <Text
            strong
            style={{
              color: '#fff',
              fontSize: 18,
              letterSpacing: 1,
            }}
          >
            Deep Research Agent Platform
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[selectedKey]}
          items={NAV_ITEMS}
          style={{ flex: 1, justifyContent: 'flex-end', minWidth: 200 }}
        />
      </Header>
      <Content style={{ padding: '24px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/research/:taskId" element={<ResearchProgress />} />
          <Route path="/result/:taskId" element={<ReportResult />} />
          <Route path="/knowledge" element={<KnowledgeBase />} />
        </Routes>
      </Content>
    </Layout>
  );
};

export default App;
