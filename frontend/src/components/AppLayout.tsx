import { Fragment } from "react";
import { Link, Outlet, useLocation, useParams } from "react-router-dom";

interface BreadcrumbItem {
  label: string;
  to?: string;
}

function useBreadcrumbs() {
  const location = useLocation();
  const params = useParams();
  const tableKey = params.tableKey ? decodeURIComponent(params.tableKey) : null;
  const tableName = tableKey?.startsWith("table:") ? tableKey.slice("table:".length) : tableKey;

  if (location.pathname === "/") {
    return [
      { label: "总览", to: "/" },
      { label: "表搜索" },
    ] satisfies BreadcrumbItem[];
  }
  if (location.pathname === "/objects") {
    return [
      { label: "总览", to: "/" },
      { label: "对象列表" },
    ] satisfies BreadcrumbItem[];
  }
  if (location.pathname === "/analysis/cycles") {
    return [
      { label: "总览", to: "/" },
      { label: "闭环分析" },
    ] satisfies BreadcrumbItem[];
  }
  if (location.pathname.endsWith("/impact") && tableKey) {
    return [
      { label: "总览", to: "/" },
      { label: "表详情", to: `/tables/${encodeURIComponent(tableKey)}` },
      { label: tableName ?? tableKey, to: `/tables/${encodeURIComponent(tableKey)}` },
      { label: "影响分析" },
    ] satisfies BreadcrumbItem[];
  }
  if (tableKey) {
    return [
      { label: "总览", to: "/" },
      { label: "表详情" },
      { label: tableName ?? tableKey },
    ] satisfies BreadcrumbItem[];
  }
  return [
    { label: "总览", to: "/" },
    { label: "表搜索" },
  ] satisfies BreadcrumbItem[];
}

export function AppLayout() {
  const breadcrumbs = useBreadcrumbs();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <Link to="/" className="topbar-home">
            BloodLine
          </Link>
          <span className="topbar-tag">数据血缘分析</span>
        </div>
        <nav className="topbar-nav" aria-label="主导航">
          <Link to="/">总览</Link>
          <Link to="/#table-search">表搜索</Link>
          <Link to="/analysis/cycles">闭环分析</Link>
        </nav>
        <div className="topbar-location" aria-label="面包屑">
          <span className="topbar-location-label">当前位置</span>
          <strong className="topbar-breadcrumbs">
            {breadcrumbs.map((item, index) => (
              <Fragment key={`${item.label}-${index}`}>
                {index > 0 ? <span className="topbar-breadcrumb-separator">/</span> : null}
                {item.to ? <Link to={item.to}>{item.label}</Link> : <span>{item.label}</span>}
              </Fragment>
            ))}
          </strong>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
