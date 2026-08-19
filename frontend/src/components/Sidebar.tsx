import React from 'react';

interface SidebarProps {
  activePage: string;
  onNavigate: (page: string) => void;
  schema: any;
}

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: '◉' },
  { id: 'structure', label: 'Structure', icon: '⊞' },
  { id: 'statistics', label: 'Statistics', icon: '≡' },
  { id: 'quality', label: 'Quality', icon: '◎' },
  { id: 'classes', label: 'Classes', icon: '⊕', requires: 'labels' },
  { id: 'images', label: 'Images', icon: '▣', requires: 'images' },
  { id: 'duplicates', label: 'Duplicates', icon: '⊜' },
  { id: 'examples', label: 'Examples', icon: '⊡' },
];

export default function Sidebar({ activePage, onNavigate, schema }: SidebarProps) {
  const capabilities = schema?.capabilities || [];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <h1>Dataset Inspector</h1>
        <p>v0.1.0</p>
      </div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(item => {
          // Hide items that require capabilities not present
          if (item.requires && !capabilities.includes(item.requires)) {
            return null;
          }

          return (
            <button
              key={item.id}
              className={`sidebar-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <span className="sidebar-item-icon">{item.icon}</span>
              {item.label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
