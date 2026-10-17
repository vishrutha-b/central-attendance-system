/**
 * CAMS API Client
 * Enterprise Central Attendance Management System (CAMS)
 */

class CamsApiClient {
  constructor() {
    // Detect base API URL
    const isStandalone = window.location.protocol === 'file:' || 
                         window.location.port === '5500' || 
                         window.location.port === '3000';
    this.baseUrl = isStandalone ? 'http://localhost:8000' : window.location.origin;
    this.tokenKey = 'cams_access_token';
    this.userKey = 'cams_current_user';
    this.tenantKey = 'cams_current_tenant';
  }

  getTenantId() {
    return localStorage.getItem(this.tenantKey) || 'default';
  }

  setTenantId(tenantId) {
    if (tenantId) {
      localStorage.setItem(this.tenantKey, tenantId);
    } else {
      localStorage.removeItem(this.tenantKey);
    }
  }

  getToken() {
    return localStorage.getItem(this.tokenKey);
  }

  setToken(token) {
    if (token) {
      localStorage.setItem(this.tokenKey, token);
    } else {
      localStorage.removeItem(this.tokenKey);
    }
  }

  getCurrentUser() {
    const raw = localStorage.getItem(this.userKey);
    return raw ? JSON.parse(raw) : null;
  }

  setCurrentUser(user) {
    if (user) {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    } else {
      localStorage.removeItem(this.userKey);
    }
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const tenantId = this.getTenantId();
    if (tenantId) {
      headers['X-Tenant-ID'] = tenantId;
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      
      // Handle 204 No Content
      if (response.status === 204) {
        return null;
      }

      // Handle CSV or file blob downloads
      const contentType = response.headers.get('content-type') || '';
      if (contentType.includes('text/csv')) {
        return await response.blob();
      }

      const data = await response.json();

      if (!response.ok) {
        // Format structured error
        let errorMessage = data.detail || data.error || 'Server request failed';
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg}`).join(', ');
        }
        const error = new Error(errorMessage);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.status === 401 && !endpoint.includes('/auth/login')) {
        // Token expired or invalid
        console.warn('Authentication token expired or required.');
      }
      throw err;
    }
  }

  // ── Health Probes ───────────────────────────────────────────
  async checkLive() {
    return this.request('/health/live');
  }

  async checkReady() {
    return this.request('/health/ready');
  }

  // ── Auth APIs ───────────────────────────────────────────────
  parseJwt(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      return null;
    }
  }

  async login(username, password, tenantId = null) {
    const activeTenant = tenantId || this.getTenantId();
    const result = await this.request('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password, tenant_id: activeTenant }),
    });

    if (result && result.access_token) {
      this.setToken(result.access_token);
      if (result.tenant_id) {
        this.setTenantId(result.tenant_id);
      }
      const payload = this.parseJwt(result.access_token) || {};
      try {
        const me = await this.getMe();
        this.setCurrentUser({ ...payload, ...me, tenant_id: result.tenant_id || activeTenant });
      } catch (e) {
        this.setCurrentUser({
          username: payload.username || username,
          role: payload.role || (username.toUpperCase().startsWith('EMP-') ? 'employee' : 'admin'),
          employee_id: payload.employee_id || (payload.role === 'employee' ? payload.sub : null),
          name: payload.name || username,
          tenant_id: result.tenant_id || activeTenant,
        });
      }
    }
    return result;
  }

  async registerAdmin(payload) {
    if (!payload.tenant_id) {
      payload.tenant_id = this.getTenantId();
    }
    const result = await this.request('/api/v1/auth/register/admin', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (result && result.access_token) {
      this.setToken(result.access_token);
      if (result.tenant_id) {
        this.setTenantId(result.tenant_id);
      }
      const tokenPayload = this.parseJwt(result.access_token) || {};
      this.setCurrentUser({
        username: payload.username,
        role: 'admin',
        name: payload.name || payload.username,
        tenant_id: result.tenant_id || payload.tenant_id,
        ...tokenPayload,
      });
    }
    return result;
  }

  async registerEmployee(payload) {
    if (!payload.tenant_id) {
      payload.tenant_id = this.getTenantId();
    }
    const result = await this.request('/api/v1/auth/register/employee', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    if (result && result.access_token) {
      this.setToken(result.access_token);
      if (result.tenant_id) {
        this.setTenantId(result.tenant_id);
      }
      const tokenPayload = this.parseJwt(result.access_token) || {};
      this.setCurrentUser({
        username: payload.employee_id || tokenPayload.sub,
        employee_id: payload.employee_id || tokenPayload.sub,
        name: payload.name,
        role: 'employee',
        department: payload.department,
        tenant_id: result.tenant_id || payload.tenant_id,
        ...tokenPayload,
      });
    }
    return result;
  }

  async getMe() {
    return this.request('/api/v1/auth/me');
  }

  async forgotPassword(email, tenantId = null) {
    const activeTenant = tenantId || this.getTenantId();
    return this.request('/api/v1/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email, tenant_id: activeTenant }),
    });
  }

  async verifyResetCode(email, code, tenantId = null) {
    const activeTenant = tenantId || this.getTenantId();
    return this.request('/api/v1/auth/verify-reset-code', {
      method: 'POST',
      body: JSON.stringify({ email, code, tenant_id: activeTenant }),
    });
  }

  async resetPassword(email, code, newPassword, tenantId = null) {
    const activeTenant = tenantId || this.getTenantId();
    return this.request('/api/v1/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ email, code, new_password: newPassword, tenant_id: activeTenant }),
    });
  }

  logout() {
    this.setToken(null);
    this.setCurrentUser(null);
  }

  // ── Attendance Tracking ─────────────────────────────────────
  async recordEntry(employeeId, entryTime = null, date = null, deviceId = null) {
    const payload = { employee_id: employeeId };
    if (entryTime) payload.entry_time = entryTime;
    if (date) payload.date = date;
    if (deviceId) payload.device_id = deviceId;
    return this.request('/api/v1/attendance/entry', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async recordExit(employeeId, exitTime = null, date = null, deviceId = null) {
    const payload = { employee_id: employeeId };
    if (exitTime) payload.exit_time = exitTime;
    if (date) payload.date = date;
    if (deviceId) payload.device_id = deviceId;
    return this.request('/api/v1/attendance/exit', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async quickRecord(employeeId, date = null, entryTime = null, exitTime = null) {
    const payload = { employee_id: employeeId };
    if (date) payload.date = date;
    if (entryTime) payload.entry_time = entryTime;
    if (exitTime) payload.exit_time = exitTime;
    return this.request('/api/v1/attendance/quick-record', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getAttendanceForDate(employeeId, dateStr) {
    return this.request(`/api/v1/attendance/${encodeURIComponent(employeeId)}?date=${encodeURIComponent(dateStr)}`);
  }

  async getAttendanceHistory(employeeId, params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    return this.request(`/api/v1/attendance/${encodeURIComponent(employeeId)}/history?${query.toString()}`);
  }

  async regularizeAttendance(attendanceId, data) {
    return this.request(`/api/v1/attendance/session/${encodeURIComponent(attendanceId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // ── Employees Directory ─────────────────────────────────────
  async listEmployees(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    if (params.search) query.append('search', params.search);
    if (params.department) query.append('department', params.department);
    if (typeof params.is_active === 'boolean') query.append('is_active', params.is_active);
    return this.request(`/api/v1/employees?${query.toString()}`);
  }

  async getEmployee(employeeId) {
    return this.request(`/api/v1/employees/${encodeURIComponent(employeeId)}`);
  }

  async createEmployee(data) {
    return this.request('/api/v1/employees', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateEmployee(employeeId, data) {
    return this.request(`/api/v1/employees/${encodeURIComponent(employeeId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteEmployee(employeeId) {
    return this.request(`/api/v1/employees/${encodeURIComponent(employeeId)}`, {
      method: 'DELETE',
    });
  }

  // ── Leave & Holidays ────────────────────────────────────────
  async submitLeave(data) {
    return this.request('/api/v1/leave', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listLeaves(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    if (params.employee_id) query.append('employee_id', params.employee_id);
    if (params.status) query.append('status', params.status);
    return this.request(`/api/v1/leave?${query.toString()}`);
  }

  async getLeave(leaveId) {
    return this.request(`/api/v1/leave/${encodeURIComponent(leaveId)}`);
  }

  async approveLeave(leaveId, note = null) {
    return this.request(`/api/v1/leave/${encodeURIComponent(leaveId)}/approve`, {
      method: 'PATCH',
      body: JSON.stringify({ note: note || 'Approved by administrator' }),
    });
  }

  async rejectLeave(leaveId, reason) {
    return this.request(`/api/v1/leave/${encodeURIComponent(leaveId)}/reject`, {
      method: 'PATCH',
      body: JSON.stringify({ reason }),
    });
  }

  async listHolidays(year = null) {
    const query = year ? `?year=${year}` : '';
    return this.request(`/api/v1/holidays${query}`);
  }

  async createHoliday(data) {
    return this.request('/api/v1/holidays', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Reports & Compliance Analytics ──────────────────────────
  async getAttendanceReport(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.department) query.append('department', params.department);
    if (params.employee_id) query.append('employee_id', params.employee_id);
    return this.request(`/api/v1/reports/attendance?${query.toString()}`);
  }

  getExportCsvUrl(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.department) query.append('department', params.department);
    return `${this.baseUrl}/api/v1/reports/attendance/export.csv?${query.toString()}`;
  }

  async downloadExportCsv(params = {}) {
    const query = new URLSearchParams();
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    if (params.department) query.append('department', params.department);
    return this.request(`/api/v1/reports/attendance/export.csv?${query.toString()}`);
  }

  // ── Admin Security & Audits ─────────────────────────────────
  async listAuditLogs(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    if (params.action) query.append('action', params.action);
    if (params.resource_type) query.append('resource_type', params.resource_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    return this.request(`/api/v1/admin/audit-logs?${query.toString()}`);
  }

  async triggerWeeklyMonitoring(payload = {}) {
    return this.request('/api/v1/admin/monitoring/run', {
      method: 'POST',
      body: JSON.stringify({
        target_week_start: payload.target_week_start || null,
        include_current_week: payload.include_current_week !== undefined ? payload.include_current_week : true,
        force_resend: payload.force_resend !== undefined ? payload.force_resend : false,
      }),
    });
  }

  async listAdminUsers(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    return this.request(`/api/v1/admin/users?${query.toString()}`);
  }

  async createAdminUser(data) {
    return this.request('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Real-Time Presence ───────────────────────────────────────
  async getLivePresence(department = null) {
    const query = department ? `?department=${encodeURIComponent(department)}` : '';
    return this.request(`/api/v1/attendance/live-presence${query}`);
  }

  // ── Regularization Workflow ─────────────────────────────────
  async submitRegularization(data) {
    return this.request('/api/v1/attendance/regularize', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async listRegularizations(params = {}) {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.page_size) query.append('page_size', params.page_size);
    if (params.employee_id) query.append('employee_id', params.employee_id);
    if (params.status) query.append('status', params.status);
    return this.request(`/api/v1/attendance/regularize?${query.toString()}`);
  }

  async reviewRegularization(requestId, action, reviewerNotes = null) {
    return this.request(`/api/v1/attendance/regularize/${encodeURIComponent(requestId)}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        action,
        reviewer_notes: reviewerNotes,
      }),
    });
  }

  // ── Leave Balances & Quotas ─────────────────────────────────
  async getLeaveBalances(employeeId, year = 2026) {
    return this.request(`/api/v1/leave/balances/${encodeURIComponent(employeeId)}?year=${year}`);
  }

  async allocateLeaveBalance(data) {
    return this.request('/api/v1/leave/balances/allocate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // ── Tenant Organization Management ──────────────────────────
  async getTenants(skip = 0, limit = 50) {
    return this.request(`/api/v1/tenants?skip=${skip}&limit=${limit}`);
  }

  async getTenant(tenantId) {
    return this.request(`/api/v1/tenants/${encodeURIComponent(tenantId)}`);
  }

  async onboardTenant(tenantData) {
    return this.request('/api/v1/tenants', {
      method: 'POST',
      body: JSON.stringify(tenantData),
    });
  }

  async updateTenant(tenantId, updateData) {
    return this.request(`/api/v1/tenants/${encodeURIComponent(tenantId)}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
  }
}

// Global API singleton
window.camsApi = new CamsApiClient();
