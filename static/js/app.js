/**
 * Central Attendance Management System (CAMS)
 * Clean SaaS Application Logic with Role-Based Access Control (Admin & Employee)
 */

document.addEventListener('DOMContentLoaded', () => {
  const app = {
    state: {
      currentView: 'dashboard',
      theme: localStorage.getItem('cams_theme') || 'light',
      employees: [],
      leaves: [],
      holidays: [],
      metrics: {
        totalEmployees: 0,
        pendingLeaves: 0,
      },
      currentUser: window.camsApi.getCurrentUser(),
    },

    async init() {
      this.initTheme();
      this.initNavigation();
      this.initModals();
      this.initForms();
      this.initPunchTerminal();
      this.initAuthGate();
      this.initSignout();

      // Check authentication state: Show Login Gate if not authenticated
      const authGate = document.getElementById('view-auth-gate');
      const appShell = document.getElementById('app-shell');

      if (window.camsApi.isAuthenticated()) {
        if (authGate) authGate.style.display = 'none';
        if (appShell) appShell.style.display = 'block';
        this.applyRolePermissions();
        await this.refreshAllData();
      } else {
        if (authGate) authGate.style.display = 'flex';
        if (appShell) appShell.style.display = 'none';
      }

      await this.checkSystemHealth();
      setInterval(() => this.checkSystemHealth(), 15000);
    },

    // ── Theme Management ────────────────────────────────────────
    initTheme() {
      document.documentElement.setAttribute('data-theme', this.state.theme);
      const themeToggleBtn = document.getElementById('theme-toggle-btn');
      if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
          this.state.theme = this.state.theme === 'light' ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', this.state.theme);
          localStorage.setItem('cams_theme', this.state.theme);
        });
      }
    },

    // ── Navigation ──────────────────────────────────────────────
    initNavigation() {
      const tabBtns = document.querySelectorAll('[data-tab]');
      tabBtns.forEach((btn) => {
        btn.addEventListener('click', () => {
          const tabName = btn.getAttribute('data-tab');
          if (tabName) this.switchView(tabName);
        });
      });
    },

    switchView(viewId) {
      this.state.currentView = viewId;

      document.querySelectorAll('[data-tab]').forEach((btn) => {
        if (btn.getAttribute('data-tab') === viewId) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      document.querySelectorAll('.tab-view').forEach((view) => {
        if (view.id === `view-${viewId}`) {
          view.classList.add('active');
        } else {
          view.classList.remove('active');
        }
      });

      if (viewId === 'employees') this.loadEmployeesView();
      if (viewId === 'attendance') this.loadAttendanceView();
      if (viewId === 'leave') this.loadLeaveView();
      if (viewId === 'reports') this.loadReportsView();
      if (viewId === 'audit') this.loadAuditView();
      if (viewId === 'tenants') this.loadTenantsView();
    },

    // ── System Health ───────────────────────────────────────────
    async checkSystemHealth() {
      const dot = document.getElementById('health-indicator-dot');
      const text = document.getElementById('health-indicator-text');
      try {
        const live = await window.camsApi.checkLive();
        const ready = await window.camsApi.checkReady();
        if (live.status === 'ok' && ready.status === 'ready') {
          if (dot) dot.className = 'health-dot';
          if (text) text.textContent = 'System Live';
        } else {
          throw new Error('Down');
        }
      } catch (e) {
        if (dot) dot.className = 'health-dot down';
        if (text) text.textContent = 'Backend Offline';
      }
    },

    // ── Dedicated Authentication Gate (Login Screen) ────────────
    initAuthGate() {
      let currentRole = 'admin'; // 'admin' or 'employee'
      let currentMode = 'signin'; // 'signin' or 'register'

      const tabAdmin = document.getElementById('auth-tab-admin');
      const tabEmployee = document.getElementById('auth-tab-employee');
      const modeSignin = document.getElementById('auth-mode-signin');
      const modeRegister = document.getElementById('auth-mode-register');
      const labelUser = document.getElementById('auth-label-username');
      const descText = document.getElementById('auth-role-description');
      const userInput = document.getElementById('auth-input-username');
      const passInput = document.getElementById('auth-input-password');
      const submitBtn = document.getElementById('auth-btn-submit');
      const errorBox = document.getElementById('auth-error-message');
      const loginForm = document.getElementById('auth-login-form');
      const registerForm = document.getElementById('auth-register-form');
      const regAdminFields = document.getElementById('auth-reg-admin-fields');
      const regEmployeeFields = document.getElementById('auth-reg-employee-fields');
      const regSubmitBtn = document.getElementById('auth-btn-reg-submit');
      const switchToReg = document.getElementById('auth-switch-to-register');
      const switchToSign = document.getElementById('auth-switch-to-signin');

      const updateUI = () => {
        if (errorBox) errorBox.classList.remove('visible');

        // Role tabs
        if (currentRole === 'admin') {
          tabAdmin?.classList.add('active');
          tabEmployee?.classList.remove('active');
          if (regAdminFields) regAdminFields.style.display = 'flex';
          if (regEmployeeFields) regEmployeeFields.style.display = 'none';
          if (labelUser) labelUser.innerHTML = '<span>Admin Username</span>';
          if (userInput) userInput.placeholder = 'Enter admin username';
          if (submitBtn) submitBtn.textContent = 'Sign In as Administrator →';
          if (regSubmitBtn) regSubmitBtn.textContent = 'Create Administrator Account →';
        } else {
          tabEmployee?.classList.add('active');
          tabAdmin?.classList.remove('active');
          if (regAdminFields) regAdminFields.style.display = 'none';
          if (regEmployeeFields) regEmployeeFields.style.display = 'flex';
          if (labelUser) labelUser.innerHTML = '<span>Employee ID or Email</span>';
          if (userInput) userInput.placeholder = 'Enter Employee ID or email';
          if (submitBtn) submitBtn.textContent = 'Sign In as Employee →';
          if (regSubmitBtn) regSubmitBtn.textContent = 'Create Employee Account →';
        }

        // Mode switch
        if (currentMode === 'signin') {
          modeSignin?.classList.add('active');
          modeRegister?.classList.remove('active');
          if (modeSignin) {
            modeSignin.style.color = 'var(--primary)';
            modeSignin.style.borderBottomColor = 'var(--primary)';
          }
          if (modeRegister) {
            modeRegister.style.color = 'var(--text-muted)';
            modeRegister.style.borderBottomColor = 'transparent';
          }
          if (loginForm) loginForm.style.display = 'flex';
          if (registerForm) registerForm.style.display = 'none';
          if (descText) {
            descText.innerHTML = currentRole === 'admin'
              ? '<strong>Administrator Sign In:</strong> Enter your admin username and password to log in.'
              : '<strong>Employee Sign In:</strong> Enter your Employee ID (or email) and your password to log in.';
          }
        } else {
          modeRegister?.classList.add('active');
          modeSignin?.classList.remove('active');
          if (modeRegister) {
            modeRegister.style.color = 'var(--primary)';
            modeRegister.style.borderBottomColor = 'var(--primary)';
          }
          if (modeSignin) {
            modeSignin.style.color = 'var(--text-muted)';
            modeSignin.style.borderBottomColor = 'transparent';
          }
          if (loginForm) loginForm.style.display = 'none';
          if (registerForm) registerForm.style.display = 'flex';
          if (descText) {
            descText.innerHTML = currentRole === 'admin'
              ? '<strong>Create Administrator Account:</strong> Register your admin username and choose your password.'
              : '<strong>Create Employee Account:</strong> Register your employee profile and set your personal password.';
          }
        }
      };

      tabAdmin?.addEventListener('click', () => { currentRole = 'admin'; updateUI(); });
      tabEmployee?.addEventListener('click', () => { currentRole = 'employee'; updateUI(); });
      modeSignin?.addEventListener('click', () => { currentMode = 'signin'; updateUI(); });
      modeRegister?.addEventListener('click', () => { currentMode = 'register'; updateUI(); });
      switchToReg?.addEventListener('click', (e) => { e.preventDefault(); currentMode = 'register'; updateUI(); });
      switchToSign?.addEventListener('click', (e) => { e.preventDefault(); currentMode = 'signin'; updateUI(); });

      // Initial clean state
      updateUI();

      // Sign In Form Handler
      loginForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const tenantInput = document.getElementById('auth-input-tenant');
        const tenantId = tenantInput?.value.trim() || 'default';
        const username = userInput?.value.trim() || '';
        const password = passInput?.value || '';

        if (!username || !password) {
          if (errorBox) {
            errorBox.textContent = 'Please enter both username/ID and password.';
            errorBox.classList.add('visible');
          }
          return;
        }

        const prevBtnText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Verifying credentials...';
        }
        if (errorBox) errorBox.classList.remove('visible');

        try {
          await window.camsApi.login(username, password, tenantId);
          this.state.currentUser = window.camsApi.getCurrentUser();

          // Transition to Authenticated Shell
          const authGate = document.getElementById('view-auth-gate');
          const appShell = document.getElementById('app-shell');
          if (authGate) authGate.style.display = 'none';
          if (appShell) appShell.style.display = 'block';

          this.applyRolePermissions();
          const isEmp = this.state.currentUser?.role === 'employee';
          const roleLabel = isEmp ? 'Employee' : 'Administrator';
          const displayName = this.state.currentUser?.name || username;
          this.showToast('success', `Signed in as ${roleLabel}: ${displayName}`);

          await this.refreshAllData();
        } catch (err) {
          if (errorBox) {
            errorBox.textContent = `Sign in failed: ${err.message}`;
            errorBox.classList.add('visible');
          }
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = prevBtnText;
          }
        }
      });

      // Register Form Handler
      registerForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const tenantId = document.getElementById('auth-reg-tenant-id')?.value.trim() || 'default';
        const email = document.getElementById('auth-reg-email')?.value.trim();
        const password = document.getElementById('auth-reg-password')?.value;
        const confirmPassword = document.getElementById('auth-reg-confirm-password')?.value;

        if (password !== confirmPassword) {
          if (errorBox) {
            errorBox.textContent = 'Passwords do not match. Please verify.';
            errorBox.classList.add('visible');
          }
          return;
        }

        if (password.length < 6) {
          if (errorBox) {
            errorBox.textContent = 'Password must be at least 6 characters long.';
            errorBox.classList.add('visible');
          }
          return;
        }

        const prevBtnText = regSubmitBtn ? regSubmitBtn.textContent : '';
        if (regSubmitBtn) {
          regSubmitBtn.disabled = true;
          regSubmitBtn.textContent = 'Creating account...';
        }
        if (errorBox) errorBox.classList.remove('visible');

        try {
          if (currentRole === 'admin') {
            const username = document.getElementById('auth-reg-admin-username')?.value.trim();
            const name = document.getElementById('auth-reg-admin-name')?.value.trim();
            if (!username) throw new Error('Please choose an admin username.');
            await window.camsApi.registerAdmin({ username, email, password, name, tenant_id: tenantId });
          } else {
            const empId = document.getElementById('auth-reg-emp-id')?.value.trim();
            const name = document.getElementById('auth-reg-emp-name')?.value.trim();
            const department = document.getElementById('auth-reg-emp-dept')?.value;
            if (!name) throw new Error('Please enter your full name.');
            await window.camsApi.registerEmployee({
              employee_id: empId || null,
              name,
              email,
              department,
              password,
              tenant_id: tenantId,
            });
          }

          this.state.currentUser = window.camsApi.getCurrentUser();

          const authGate = document.getElementById('view-auth-gate');
          const appShell = document.getElementById('app-shell');
          if (authGate) authGate.style.display = 'none';
          if (appShell) appShell.style.display = 'block';

          this.applyRolePermissions();
          const isEmp = this.state.currentUser?.role === 'employee';
          this.showToast('success', `Account created successfully! Welcome, ${this.state.currentUser?.name || ''}`);

          await this.refreshAllData();
        } catch (err) {
          if (errorBox) {
            errorBox.textContent = `Account creation failed: ${err.message}`;
            errorBox.classList.add('visible');
          }
        } finally {
          if (regSubmitBtn) {
            regSubmitBtn.disabled = false;
            regSubmitBtn.textContent = prevBtnText;
          }
        }
      });
    },

    // ── Sign Out Handler ────────────────────────────────────────
    initSignout() {
      const signoutBtn = document.getElementById('app-signout-btn');
      signoutBtn?.addEventListener('click', () => {
        const user = window.camsApi.getCurrentUser();
        const roleLabel = user?.role === 'employee' ? 'Employee' : 'Administrator';
        if (confirm(`Sign out from ${roleLabel} session?`)) {
          window.camsApi.logout();
          this.state.currentUser = null;

          const authGate = document.getElementById('view-auth-gate');
          const appShell = document.getElementById('app-shell');
          if (appShell) appShell.style.display = 'none';
          if (authGate) authGate.style.display = 'flex';

          this.showToast('info', 'Signed out successfully. Please log in to continue.');
        }
      });
    },

    // ── Role-Based Access Control (RBAC) ────────────────────────
    applyRolePermissions() {
      const user = window.camsApi.getCurrentUser();
      const userNameEl = document.getElementById('auth-user-name');
      const userAvatarEl = document.getElementById('auth-user-avatar');
      const brandTag = document.getElementById('brand-role-subtitle');

      const isEmployee = user && user.role === 'employee';
      const isAdmin = user && (user.role === 'admin' || user.role === 'super_admin');

      // 1. Header User Pill & Brand Subtitle
      if (isEmployee) {
        const empId = user.employee_id || user.username;
        if (brandTag) brandTag.textContent = 'Employee Self-Service Portal';
        if (userNameEl) userNameEl.textContent = `${user.name || empId} (EMP)`;
        if (userAvatarEl) userAvatarEl.textContent = (user.name || empId).slice(0, 1).toUpperCase();
      } else if (isAdmin) {
        if (brandTag) brandTag.textContent = 'Administrator Portal';
        if (userNameEl) userNameEl.textContent = `Admin (${user.username})`;
        if (userAvatarEl) userAvatarEl.textContent = 'A';
      } else {
        if (brandTag) brandTag.textContent = 'Central Attendance';
        if (userNameEl) userNameEl.textContent = 'Guest';
        if (userAvatarEl) userAvatarEl.textContent = 'G';
      }

      // 2. Navigation Tab Visibility & Titles
      const navDashboard = document.querySelector('[data-tab="dashboard"]');
      const navAttendance = document.querySelector('[data-tab="attendance"]');
      const navEmployees = document.querySelector('[data-tab="employees"]');
      const navLeave = document.querySelector('[data-tab="leave"]');
      const navReports = document.querySelector('[data-tab="reports"]');
      const navAudit = document.querySelector('[data-tab="audit"]');
      const navTenants = document.getElementById('nav-tab-tenants');

      // Update active organization badge in navbar
      const tenantPill = document.getElementById('nav-active-tenant-pill');
      const tenantText = document.getElementById('nav-active-tenant-text');
      const activeTenant = window.camsApi.getTenantId() || 'default';
      if (tenantText) {
        tenantText.textContent = `🏢 Org: ${activeTenant}`;
      }
      if (tenantPill) {
        tenantPill.style.display = 'inline-flex';
      }

      if (isEmployee) {
        if (navDashboard) navDashboard.textContent = 'My Punch Station';
        if (navAttendance) navAttendance.textContent = 'My Timesheet';
        if (navLeave) navLeave.textContent = 'My Leaves';
        if (navReports) navReports.textContent = 'My Report';

        // Hide admin-only tabs
        if (navEmployees) navEmployees.style.display = 'none';
        if (navAudit) navAudit.style.display = 'none';
        if (navTenants) navTenants.style.display = 'none';

        // If currently on an admin-only view, switch to dashboard
        if (this.state.currentView === 'employees' || this.state.currentView === 'audit' || this.state.currentView === 'tenants') {
          this.switchView('dashboard');
        }
      } else {
        if (navDashboard) navDashboard.textContent = 'Dashboard';
        if (navAttendance) navAttendance.textContent = 'Timesheets';
        if (navLeave) navLeave.textContent = 'Leaves & Holidays';
        if (navReports) navReports.textContent = 'Reports';

        if (navEmployees) navEmployees.style.display = '';
        if (navAudit) navAudit.style.display = '';
        if (navTenants) navTenants.style.display = '';
      }

      // 3. Dashboard Column & Banner Views
      const empWelcomeBanner = document.getElementById('employee-welcome-banner');
      const adminKpiGrid = document.getElementById('admin-kpi-grid');
      const adminRosterCol = document.getElementById('admin-workforce-roster-col');
      const empPolicyCol = document.getElementById('employee-policy-info-col');
      const punchImmutableNotice = document.getElementById('punch-immutable-notice');

      if (isEmployee) {
        if (empWelcomeBanner) {
          empWelcomeBanner.style.display = 'flex';
          const nameEl = document.getElementById('emp-banner-name');
          const idEl = document.getElementById('emp-banner-id');
          const deptEl = document.getElementById('emp-banner-dept');
          const avatarEl = document.getElementById('emp-banner-avatar');
          if (nameEl) nameEl.textContent = `Welcome, ${user.name || user.employee_id}`;
          if (idEl) idEl.textContent = user.employee_id || user.username;
          if (deptEl) deptEl.textContent = user.department || 'Workforce Member';
          if (avatarEl) avatarEl.textContent = (user.name || user.employee_id || 'E')[0].toUpperCase();
        }
        if (adminKpiGrid) adminKpiGrid.style.display = 'none';
        if (adminRosterCol) adminRosterCol.style.display = 'none';
        if (empPolicyCol) empPolicyCol.style.display = 'block';
        if (punchImmutableNotice) punchImmutableNotice.style.display = 'block';
      } else {
        if (empWelcomeBanner) empWelcomeBanner.style.display = 'none';
        if (adminKpiGrid) adminKpiGrid.style.display = 'grid';
        if (adminRosterCol) adminRosterCol.style.display = 'block';
        if (empPolicyCol) empPolicyCol.style.display = 'none';
        if (punchImmutableNotice) punchImmutableNotice.style.display = 'none';
      }

      // 4. Punch Terminal Field Controls
      const punchEmpInput = document.getElementById('punch-employee-id');
      const quickRecordBtn = document.querySelector('.punch-mode-btn[data-mode="quick"]');

      if (isEmployee) {
        const myId = user.employee_id || user.username;
        if (punchEmpInput) {
          punchEmpInput.value = myId;
          punchEmpInput.readOnly = true;
          punchEmpInput.style.backgroundColor = 'var(--bg-subtle)';
          punchEmpInput.title = 'Locked to your authenticated employee account';
        }
        if (quickRecordBtn) quickRecordBtn.style.display = 'none';
      } else {
        if (punchEmpInput) {
          punchEmpInput.readOnly = false;
          punchEmpInput.style.backgroundColor = '';
          punchEmpInput.title = '';
        }
        if (quickRecordBtn) quickRecordBtn.style.display = '';
      }

      // 5. Leave Request Form Controls
      const leaveEmpInput = document.getElementById('leave-emp-id');
      const regReqEmpInput = document.getElementById('reg-req-emp-id');
      if (isEmployee) {
        const empId = user.employee_id || user.username;
        if (leaveEmpInput) {
          leaveEmpInput.value = empId;
          leaveEmpInput.readOnly = true;
        }
        if (regReqEmpInput) {
          regReqEmpInput.value = empId;
          regReqEmpInput.readOnly = true;
        }
      } else {
        if (leaveEmpInput) leaveEmpInput.readOnly = false;
        if (regReqEmpInput) regReqEmpInput.readOnly = false;
      }
    },

    // ── Punch Terminal ──────────────────────────────────────────
    initPunchTerminal() {
      const modeTabs = document.querySelectorAll('.punch-mode-btn[data-mode]');
      modeTabs.forEach((tab) => {
        tab.addEventListener('click', () => {
          modeTabs.forEach((t) => t.classList.remove('active'));
          tab.classList.add('active');
          const mode = tab.getAttribute('data-mode');
          this.switchPunchMode(mode);
        });
      });

      const entryInput = document.getElementById('punch-entry-time');
      const exitInput = document.getElementById('punch-exit-time');
      const calcHoursNum = document.getElementById('calc-hours-number');
      const calcFill = document.getElementById('calc-progress-fill');
      const calcBadge = document.getElementById('calc-status-badge');
      const calcNotice = document.getElementById('calc-notice-text');

      const recalculatePreview = () => {
        const entryVal = entryInput?.value?.trim();
        const exitVal = exitInput?.value?.trim();

        if (!entryVal || !exitVal) {
          if (calcHoursNum) calcHoursNum.textContent = '0.00';
          if (calcFill) calcFill.style.width = '0%';
          if (calcBadge) {
            calcBadge.className = 'estimator-badge';
            calcBadge.textContent = 'Ready';
          }
          if (calcNotice) calcNotice.textContent = 'Policy rule: ≥ 5.0h required. Exits under 5h send immediate email alert.';
          return;
        }

        const entryParts = entryVal.split(':').map(Number);
        const exitParts = exitVal.split(':').map(Number);
        if (entryParts.length >= 2 && exitParts.length >= 2) {
          let diffMinutes = (exitParts[0] * 60 + exitParts[1]) - (entryParts[0] * 60 + entryParts[1]);
          if (diffMinutes < 0) diffMinutes += 24 * 60;
          const hours = Number((diffMinutes / 60).toFixed(2));

          if (calcHoursNum) calcHoursNum.textContent = hours.toFixed(2);

          const percent = Math.min(100, Math.round((hours / 5.0) * 100));
          if (calcFill) {
            calcFill.style.width = `${percent}%`;
            calcFill.className = `meter-fill ${hours >= 5.0 ? 'compliant' : 'deficit'}`;
          }

          if (hours >= 5.0) {
            if (calcBadge) {
              calcBadge.className = 'estimator-badge compliant';
              calcBadge.textContent = 'Compliant';
            }
            if (calcNotice) calcNotice.textContent = 'Session fulfills mandatory daily 5.0h requirement.';
          } else {
            const deficit = (5.0 - hours).toFixed(2);
            if (calcBadge) {
              calcBadge.className = 'estimator-badge deficit';
              calcBadge.textContent = `Deficit (-${deficit}h)`;
            }
            if (calcNotice) calcNotice.textContent = `Warning: Alert notice will be emailed to employee upon exit (-${deficit}h deficit).`;
          }
        }
      };

      entryInput?.addEventListener('input', recalculatePreview);
      exitInput?.addEventListener('input', recalculatePreview);

      document.getElementById('use-now-entry')?.addEventListener('click', () => {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        if (entryInput) entryInput.value = `${hh}:${mm}`;
        recalculatePreview();
      });

      document.getElementById('use-now-exit')?.addEventListener('click', () => {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, '0');
        const mm = String(now.getMinutes()).padStart(2, '0');
        if (exitInput) exitInput.value = `${hh}:${mm}`;
        recalculatePreview();
      });

      document.getElementById('preset-deficit-demo')?.addEventListener('click', () => {
        const user = window.camsApi.getCurrentUser();
        if (!user || user.role !== 'employee') {
          document.getElementById('punch-employee-id').value = 'EMP-007';
        }
        if (entryInput) entryInput.value = '09:00';
        if (exitInput) exitInput.value = '12:00';
        recalculatePreview();
      });

      document.getElementById('preset-compliant-demo')?.addEventListener('click', () => {
        const user = window.camsApi.getCurrentUser();
        if (!user || user.role !== 'employee') {
          document.getElementById('punch-employee-id').value = 'EMP-007';
        }
        if (entryInput) entryInput.value = '09:00';
        if (exitInput) exitInput.value = '17:30';
        recalculatePreview();
      });
    },

    switchPunchMode(mode) {
      const exitGroup = document.getElementById('punch-exit-group');
      const entryGroup = document.getElementById('punch-entry-group');
      const submitBtn = document.getElementById('punch-submit-btn');

      if (mode === 'entry') {
        if (entryGroup) entryGroup.style.display = 'flex';
        if (exitGroup) exitGroup.style.display = 'none';
        if (submitBtn) {
          submitBtn.className = 'btn btn-primary btn-block';
          submitBtn.textContent = 'Record Clock-In';
        }
      } else if (mode === 'exit') {
        if (entryGroup) entryGroup.style.display = 'none';
        if (exitGroup) exitGroup.style.display = 'flex';
        if (submitBtn) {
          submitBtn.className = 'btn btn-danger btn-block';
          submitBtn.textContent = 'Record Clock-Out & Check Policy';
        }
      } else if (mode === 'quick') {
        if (entryGroup) entryGroup.style.display = 'flex';
        if (exitGroup) exitGroup.style.display = 'flex';
        if (submitBtn) {
          submitBtn.className = 'btn btn-primary btn-block';
          submitBtn.textContent = 'Quick Record Full Day';
        }
      }
    },

    // ── Form Submissions ────────────────────────────────────────
    initForms() {
      // 1. Punch Submit
      document.getElementById('punch-terminal-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await this.handlePunchSubmit();
      });

      // 2. Login Form
      document.getElementById('login-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        try {
          await window.camsApi.login(username, password);
          this.state.currentUser = window.camsApi.getCurrentUser();
          this.applyRolePermissions();
          this.closeModal('modal-login');
          const isEmp = this.state.currentUser?.role === 'employee';
          this.showToast('success', `Signed in as ${isEmp ? 'Employee' : 'Admin'}: ${username}`);
          await this.refreshAllData();
        } catch (err) {
          this.showToast('error', `Login failed: ${err.message}`);
        }
      });

      // 3. New Employee (Admin only)
      document.getElementById('new-employee-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          employee_id: document.getElementById('emp-id').value.trim(),
          name: document.getElementById('emp-name').value.trim(),
          email: document.getElementById('emp-email').value.trim(),
          department: document.getElementById('emp-department').value.trim(),
          role: document.getElementById('emp-role').value.trim() || 'Employee',
          password: document.getElementById('emp-password')?.value || null,
        };
        try {
          await window.camsApi.createEmployee(payload);
          this.closeModal('modal-new-employee');
          document.getElementById('new-employee-form').reset();
          this.showToast('success', `Registered ${payload.name} (${payload.employee_id})`);
          await this.refreshAllData();
          if (this.state.currentView === 'employees') await this.loadEmployeesView();
        } catch (err) {
          this.showToast('error', `Employee creation failed: ${err.message}`);
        }
      });

      // 4. Leave Request
      document.getElementById('leave-request-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = window.camsApi.getCurrentUser();
        const empId = (user && user.role === 'employee') 
          ? (user.employee_id || user.username) 
          : document.getElementById('leave-emp-id').value.trim();

        const payload = {
          employee_id: empId,
          leave_type: document.getElementById('leave-type').value,
          start_date: document.getElementById('leave-start-date').value,
          end_date: document.getElementById('leave-end-date').value,
          reason: document.getElementById('leave-reason').value.trim(),
        };
        try {
          await window.camsApi.submitLeave(payload);
          this.closeModal('modal-leave-request');
          document.getElementById('leave-request-form').reset();
          this.showToast('success', 'Leave application submitted.');
          await this.loadLeaveView();
        } catch (err) {
          this.showToast('error', `Submission error: ${err.message}`);
        }
      });

      // 5. Holiday Form (Admin only)
      document.getElementById('holiday-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          name: document.getElementById('holiday-name').value.trim(),
          date: document.getElementById('holiday-date').value,
          description: document.getElementById('holiday-desc').value.trim() || null,
        };
        try {
          await window.camsApi.createHoliday(payload);
          this.closeModal('modal-holiday');
          document.getElementById('holiday-form').reset();
          this.showToast('success', `Added holiday "${payload.name}"`);
          await this.loadLeaveView();
        } catch (err) {
          this.showToast('error', err.message);
        }
      });

      // 6. Regularize Attendance (Admin only)
      document.getElementById('regularize-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const attendanceId = document.getElementById('reg-attendance-id').value;
        const entryTime = document.getElementById('reg-entry-time').value.trim() || null;
        const exitTime = document.getElementById('reg-exit-time').value.trim() || null;
        const reason = document.getElementById('reg-reason').value.trim();

        try {
          await window.camsApi.regularizeAttendance(attendanceId, {
            entry_time: entryTime,
            exit_time: exitTime,
            reason: reason || 'Manual correction',
          });
          this.closeModal('modal-regularize');
          this.showToast('success', 'Timesheet record corrected.');
          await this.loadAttendanceView();
        } catch (err) {
          this.showToast('error', err.message);
        }
      });

      // 7. Audit Cycle (Admin only)
      document.getElementById('run-audit-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const includeCurrent = document.getElementById('audit-include-current').checked;
        const forceResend = document.getElementById('audit-force-resend').checked;
        const weekStart = document.getElementById('audit-week-start').value || null;

        try {
          const res = await window.camsApi.triggerWeeklyMonitoring({
            include_current_week: includeCurrent,
            force_resend: forceResend,
            target_week_start: weekStart,
          });
          this.closeModal('modal-run-audit');
          this.showToast('success', `Audit complete: ${res.total_evaluated || 0} evaluated.`);
          await this.loadReportsView();
        } catch (err) {
          this.showToast('error', err.message);
        }
      });

      // 8. Self-Service Attendance Regularization Request
      document.getElementById('regularization-request-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          employee_id: document.getElementById('reg-req-emp-id').value.trim(),
          date: document.getElementById('reg-req-date').value,
          requested_entry_time: document.getElementById('reg-req-entry').value.trim(),
          requested_exit_time: document.getElementById('reg-req-exit').value.trim(),
          reason: document.getElementById('reg-req-reason').value,
          notes: document.getElementById('reg-req-notes').value.trim() || null,
        };
        try {
          await window.camsApi.submitRegularization(payload);
          this.closeModal('modal-employee-regularize');
          document.getElementById('regularization-request-form').reset();
          this.showToast('success', 'Regularization request submitted for review.');
          await this.loadRegularizations();
        } catch (err) {
          this.showToast('error', `Submission error: ${err.message}`);
        }
      });

      // 9. Leave Quota Allocation (HR / Admin)
      document.getElementById('allocate-leave-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
          employee_id: document.getElementById('alloc-emp-id').value.trim(),
          year: parseInt(document.getElementById('alloc-year').value, 10),
          leave_type: document.getElementById('alloc-type').value,
          allocated_days: parseFloat(document.getElementById('alloc-days').value),
        };
        try {
          await window.camsApi.allocateLeaveBalance(payload);
          this.closeModal('modal-allocate-leave');
          document.getElementById('allocate-leave-form').reset();
          this.showToast('success', `Updated ${payload.leave_type} quota for ${payload.employee_id}`);
          await this.loadLeaveView();
        } catch (err) {
          this.showToast('error', `Allocation error: ${err.message}`);
        }
      });

      // 10. Tenant Organization Controls & Form (Admin only)
      document.getElementById('btn-open-onboard-tenant')?.addEventListener('click', () => {
        this.openModal('modal-onboard-tenant');
      });

      document.getElementById('btn-refresh-tenants')?.addEventListener('click', () => {
        this.loadTenantsView();
      });

      document.getElementById('onboard-tenant-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = document.getElementById('btn-submit-onboard-tenant');
        const prevText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) {
          submitBtn.disabled = true;
          submitBtn.textContent = 'Provisioning...';
        }

        try {
          const tenantId = document.getElementById('tenant-id-input').value.trim();
          const name = document.getElementById('tenant-name-input').value.trim();
          const contactEmail = document.getElementById('tenant-email-input').value.trim();
          const adminUsername = document.getElementById('tenant-admin-user')?.value.trim() || null;
          const adminPassword = document.getElementById('tenant-admin-pwd')?.value || null;
          const timezone = document.getElementById('tenant-tz')?.value.trim() || 'Asia/Kolkata';
          const minDays = parseInt(document.getElementById('tenant-min-days')?.value || '3', 10);
          const minHours = parseFloat(document.getElementById('tenant-min-hours')?.value || '15.0');
          const minAvg = parseFloat(document.getElementById('tenant-min-avg')?.value || '5.0');

          const payload = {
            tenant_id: tenantId,
            name,
            contact_email: contactEmail,
            admin_username: adminUsername || undefined,
            admin_password: adminPassword || undefined,
            settings: {
              company_timezone: timezone,
              timezone,
              min_days_per_week: minDays,
              min_hours_per_week: minHours,
              min_avg_hours_per_day: minAvg,
              daily_min_average_hours: minAvg,
            },
          };

          const res = await window.camsApi.onboardTenant(payload);
          this.closeModal('modal-onboard-tenant');
          document.getElementById('onboard-tenant-form').reset();
          this.showToast('success', `Organization "${res.name}" (${res.tenant_id}) provisioned successfully!`);
          await this.loadTenantsView();
        } catch (err) {
          this.showToast('error', `Failed to onboard organization: ${err.message}`);
        } finally {
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = prevText;
          }
        }
      });
    },

    async handlePunchSubmit() {
      const user = window.camsApi.getCurrentUser();
      const activeTab = document.querySelector('.punch-mode-btn[data-mode].active');
      const mode = activeTab ? activeTab.getAttribute('data-mode') : 'entry';

      let empId = document.getElementById('punch-employee-id').value.trim();
      if (user && user.role === 'employee') {
        empId = user.employee_id || user.username;
      }

      const entryTime = document.getElementById('punch-entry-time').value.trim() || null;
      const exitTime = document.getElementById('punch-exit-time').value.trim() || null;

      if (!empId) {
        this.showToast('error', 'Please sign in or specify an Employee ID');
        return;
      }

      const submitBtn = document.getElementById('punch-submit-btn');
      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = 'Processing...';

      try {
        let result;
        if (mode === 'entry') {
          result = await window.camsApi.recordEntry(empId, entryTime);
          this.showToast('success', `Clock-In saved for ${empId}`);
        } else if (mode === 'exit') {
          result = await window.camsApi.recordExit(empId, exitTime);
          if (result.policy_alert) {
            this.showPolicyAlertToast(empId, result.total_hours, result.policy_alert);
          } else {
            this.showToast('success', `Clock-Out recorded (${result.total_hours.toFixed(2)}h)`);
          }
        } else if (mode === 'quick') {
          result = await window.camsApi.quickRecord(empId, null, entryTime, exitTime);
          if (result.policy_alert) {
            this.showPolicyAlertToast(empId, result.total_hours, result.policy_alert);
          } else {
            this.showToast('success', `Day session logged (${result.total_hours.toFixed(2)}h)`);
          }
        }

        await this.refreshAllData();
      } catch (err) {
        this.showToast('error', err.message);
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    },

    // ── Toast Utility ───────────────────────────────────────────
    showPolicyAlertToast(empId, totalHours, alertMessage) {
      const container = document.getElementById('toast-container');
      if (!container) return;

      const toast = document.createElement('div');
      toast.className = 'toast toast-policy-alert';
      toast.innerHTML = `
        <div class="toast-content">
          <div class="toast-title" style="color: var(--danger);">Policy Alert Notice</div>
          <div class="toast-msg">
            <strong>${empId}</strong> logged <strong>${totalHours.toFixed(2)} hrs</strong> (&lt; 5.0h mandatory).
            Automated violation email dispatched immediately!
          </div>
        </div>
        <button class="toast-close-btn" onclick="this.parentElement.remove()">×</button>
      `;

      container.appendChild(toast);
      setTimeout(() => toast.remove(), 8000);
    },

    showToast(type, message) {
      const container = document.getElementById('toast-container');
      if (!container) return;

      const toast = document.createElement('div');
      toast.className = `toast toast-${type}`;
      toast.innerHTML = `
        <div class="toast-content">
          <div class="toast-title">${type === 'success' ? 'Success' : type === 'error' ? 'Notice' : 'Information'}</div>
          <div class="toast-msg">${message}</div>
        </div>
        <button class="toast-close-btn" onclick="this.parentElement.remove()">×</button>
      `;

      container.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    },

    // ── Modals Handling ─────────────────────────────────────────
    initModals() {
      document.querySelectorAll('[data-open-modal]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = btn.getAttribute('data-open-modal');
          this.openModal(target);
        });
      });

      document.querySelectorAll('[data-close-modal]').forEach((btn) => {
        btn.addEventListener('click', () => {
          const modal = btn.closest('.modal-backdrop');
          if (modal) modal.classList.remove('open');
        });
      });

      document.querySelectorAll('.modal-backdrop').forEach((backdrop) => {
        backdrop.addEventListener('click', (e) => {
          if (e.target === backdrop) backdrop.classList.remove('open');
        });
      });

      document.getElementById('auth-user-pill')?.addEventListener('click', () => {
        const signoutBtn = document.getElementById('app-signout-btn');
        if (signoutBtn) signoutBtn.click();
      });
    },

    openModal(id) {
      const modal = document.getElementById(id);
      if (modal) modal.classList.add('open');
    },

    closeModal(id) {
      const modal = document.getElementById(id);
      if (modal) modal.classList.remove('open');
    },

    // ── Refresh Central Data ────────────────────────────────────
    async refreshAllData() {
      try {
        const empRes = await window.camsApi.listEmployees({ page: 1, page_size: 100 });
        this.state.employees = empRes.items || [];

        const leaveRes = await window.camsApi.listLeaves({ page: 1, page_size: 50 });
        this.state.leaves = leaveRes.items || [];

        const empCountEl = document.getElementById('metric-total-employees');
        if (empCountEl) empCountEl.textContent = this.state.employees.length;

        const pendingCount = this.state.leaves.filter((l) => l.status === 'pending').length;
        const leaveCountEl = document.getElementById('metric-pending-leaves');
        if (leaveCountEl) leaveCountEl.textContent = pendingCount;

        this.renderRoster();
        await this.loadLivePresence();
      } catch (err) {
        console.warn('Sync note:', err.message);
      }
    },

    async loadLivePresence() {
      const tbody = document.getElementById('presence-table-body');
      if (!tbody) return;

      const dept = document.getElementById('presence-dept-filter')?.value || null;
      try {
        const res = await window.camsApi.getLivePresence(dept);
        
        // Update pills
        const inOfficeEl = document.getElementById('presence-count-in-office');
        const onBreakEl = document.getElementById('presence-count-on-break');
        const onLeaveEl = document.getElementById('presence-count-on-leave');
        const absentEl = document.getElementById('presence-count-absent');
        if (inOfficeEl) inOfficeEl.textContent = res.in_office_count || 0;
        if (onBreakEl) onBreakEl.textContent = res.on_break_count || 0;
        if (onLeaveEl) onLeaveEl.textContent = res.on_leave_count || 0;
        if (absentEl) absentEl.textContent = res.absent_count || 0;

        const emps = res.employees || [];
        if (!emps.length) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No employees registered.</td></tr>`;
          return;
        }

        tbody.innerHTML = emps.map((e) => {
          let badgeHtml = '';
          if (e.presence_status === 'in_office') {
            badgeHtml = `<span class="presence-stat-pill in-office" style="font-size:0.75rem; padding:3px 10px;"><span class="status-dot-pulse green"></span> In Office</span>`;
          } else if (e.presence_status === 'on_break') {
            badgeHtml = `<span class="presence-stat-pill on-break" style="font-size:0.75rem; padding:3px 10px;"><span class="status-dot-pulse amber"></span> On Break</span>`;
          } else if (e.presence_status === 'on_leave') {
            badgeHtml = `<span class="presence-stat-pill on-leave" style="font-size:0.75rem; padding:3px 10px;"><span class="status-dot-pulse blue"></span> On Leave</span>`;
          } else {
            badgeHtml = `<span class="presence-stat-pill absent" style="font-size:0.75rem; padding:3px 10px;"><span class="status-dot-pulse gray"></span> Absent / Pending</span>`;
          }

          const hoursStr = e.accumulated_hours > 0 ? `<strong>${e.accumulated_hours.toFixed(2)}h</strong>` : `<span style="color:var(--text-muted);">0.00h</span>`;

          return `
            <tr>
              <td>
                <div style="display:flex; align-items:center; gap:8px;">
                  <div class="avatar" style="width:28px; height:28px; font-size:0.75rem;">${e.name ? e.name.slice(0, 2).toUpperCase() : 'EM'}</div>
                  <div>
                    <strong style="font-size:0.86rem;">${e.name}</strong>
                    <div style="font-size:0.72rem; color:var(--text-muted);"><code>${e.employee_id}</code></div>
                  </div>
                </div>
              </td>
              <td><span style="font-size:0.82rem; color:var(--text-muted);">${e.department}</span></td>
              <td>${badgeHtml}</td>
              <td style="font-size:0.82rem;">${e.first_entry || '—'}</td>
              <td style="font-size:0.82rem;">${e.last_exit || '—'}</td>
              <td style="font-size:0.84rem;">${hoursStr}</td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--danger); padding:1rem;">Failed to load live presence: ${err.message}</td></tr>`;
      }
    },

    renderRoster() {
      const container = document.getElementById('live-activity-list');
      if (!container) return;

      if (!this.state.employees.length) {
        container.innerHTML = `
          <div class="empty-box">
            <span class="empty-title">No employees registered</span>
            <span style="font-size: 0.8rem;">Click "+ Onboard Employee" to register staff.</span>
          </div>
        `;
        return;
      }

      container.innerHTML = this.state.employees.slice(0, 7).map((emp) => {
        const initials = emp.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase();
        return `
          <div class="roster-item">
            <div class="roster-user">
              <div class="avatar">${initials}</div>
              <div>
                <div class="user-title">${emp.name}</div>
                <div class="user-desc"><code>${emp.employee_id}</code> • ${emp.department}</div>
              </div>
            </div>
            <span class="badge ${emp.is_active ? 'badge-success' : 'badge-neutral'}">
              ${emp.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        `;
      }).join('');
    },

    // ── Attendance Timesheet View ───────────────────────────────
    async loadAttendanceView() {
      const tableBody = document.getElementById('attendance-table-body');
      if (!tableBody) return;

      const user = window.camsApi.getCurrentUser();
      const isEmployee = user && user.role === 'employee';
      const myEmpId = (isEmployee ? (user.employee_id || user.username) : null) || document.getElementById('att-filter-emp')?.value.trim() || 'EMP-007';

      // Lock filter input if employee
      const filterInput = document.getElementById('att-filter-emp');
      if (filterInput) {
        if (isEmployee) {
          filterInput.value = myEmpId;
          filterInput.readOnly = true;
          filterInput.title = 'Showing your personal timesheet history';
        } else {
          filterInput.readOnly = false;
        }
      }

      tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;"><div class="spinner"></div></td></tr>`;

      try {
        const res = await window.camsApi.getAttendanceHistory(myEmpId, { page: 1, page_size: 50 });
        const items = res.items || [];

        if (!items.length) {
          tableBody.innerHTML = `
            <tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-muted);">
              No sessions found for ${myEmpId}.
            </td></tr>
          `;
          return;
        }

        tableBody.innerHTML = items.map((item) => {
          const entryStr = item.entry_time ? new Date(item.entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
          const exitStr = item.exit_time ? new Date(item.exit_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Open';
          const hours = item.total_hours ? `${item.total_hours.toFixed(2)}h` : '0.00h';
          const isCompliant = item.total_hours >= 5.0;

          const otBadge = (item.total_hours && item.total_hours > 8.0)
            ? `<span class="badge-ot" style="margin-left:4px;">OT: +${(item.total_hours - 8.0).toFixed(1)}h</span>`
            : '';

          // Edit action: Only Admin can edit. For Employees, show "Permanent"
          const actionHtml = isEmployee
            ? `<span style="font-size:0.75rem; color:var(--text-muted);">Permanent</span>`
            : `<button class="btn btn-secondary btn-sm" onclick="app.openRegularizeModal('${item.attendance_id}', '${item.employee_id}', '${entryStr}', '${exitStr}')">Edit</button>`;

          return `
            <tr>
              <td><strong>${item.date}</strong></td>
              <td><code>${item.employee_id}</code></td>
              <td>${entryStr}</td>
              <td>${exitStr}</td>
              <td><strong>${hours}</strong></td>
              <td>
                <span class="badge ${item.attendance_status === 'complete' ? 'badge-success' : 'badge-warning'}">
                  ${item.attendance_status}
                </span>
                ${item.exit_time && !isCompliant ? '<span class="badge badge-danger" style="margin-left:4px;">Deficit</span>' : ''}
                ${otBadge}
              </td>
              <td>${actionHtml}</td>
            </tr>
          `;
        }).join('');

        await this.loadRegularizations();
      } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--danger); padding:2rem;">${err.message}</td></tr>`;
      }
    },

    async loadRegularizations() {
      const tbody = document.getElementById('regularization-table-body');
      if (!tbody) return;

      const user = window.camsApi.getCurrentUser();
      const isEmployee = user && user.role === 'employee';
      const params = { page: 1, page_size: 50 };
      if (isEmployee) {
        params.employee_id = user.employee_id || user.username;
      }

      try {
        const res = await window.camsApi.listRegularizations(params);
        const items = res.items || [];

        if (!items.length) {
          tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">No regularization requests found.</td></tr>`;
          return;
        }

        tbody.innerHTML = items.map((r) => {
          const entryTimeStr = r.requested_entry_time ? new Date(r.requested_entry_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';
          const exitTimeStr = r.requested_exit_time ? new Date(r.requested_exit_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—';

          let statusBadge = '';
          if (r.status === 'approved') {
            statusBadge = `<span class="badge badge-success">Approved</span>`;
          } else if (r.status === 'rejected') {
            statusBadge = `<span class="badge badge-danger">Rejected</span>`;
          } else {
            statusBadge = `<span class="badge badge-warning">Pending Review</span>`;
          }

          let actionHtml = '';
          if (!isEmployee && r.status === 'pending') {
            actionHtml = `
              <button class="btn btn-secondary btn-sm" onclick="app.approveRegularization('${r.request_id}')">Approve</button>
              <button class="btn btn-secondary btn-sm" onclick="app.rejectRegularization('${r.request_id}')" style="color:var(--danger); margin-left:4px;">Reject</button>
            `;
          } else {
            actionHtml = `<span style="font-size:0.75rem; color:var(--text-muted);">${r.reviewer_notes || r.status}</span>`;
          }

          return `
            <tr>
              <td><code>${r.request_id}</code></td>
              <td><strong>${r.employee_id}</strong></td>
              <td>${r.date}</td>
              <td>${entryTimeStr} → ${exitTimeStr}</td>
              <td style="font-size:0.8rem; text-transform:capitalize;">${(r.reason || '').replace(/_/g, ' ')}</td>
              <td>${statusBadge}</td>
              <td>${actionHtml}</td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--danger); padding:1rem;">${err.message}</td></tr>`;
      }
    },

    async approveRegularization(requestId) {
      const note = prompt('Optional approval notes:', 'Approved by HR');
      if (note === null) return;
      try {
        await window.camsApi.reviewRegularization(requestId, 'approved', note);
        this.showToast('success', 'Regularization approved and timesheet updated.');
        await this.loadRegularizations();
        await this.loadAttendanceView();
      } catch (err) {
        this.showToast('error', err.message);
      }
    },

    async rejectRegularization(requestId) {
      const note = prompt('Reason for rejection:');
      if (!note) return;
      try {
        await window.camsApi.reviewRegularization(requestId, 'rejected', note);
        this.showToast('warning', 'Regularization rejected.');
        await this.loadRegularizations();
      } catch (err) {
        this.showToast('error', err.message);
      }
    },

    openRegularizeModal(attendanceId, empId, entryTime, exitTime) {
      const user = window.camsApi.getCurrentUser();
      if (user && user.role === 'employee') {
        alert('Employees are not authorized to edit attendance records once submitted.');
        return;
      }
      document.getElementById('reg-attendance-id').value = attendanceId;
      document.getElementById('reg-display-emp').textContent = empId;
      document.getElementById('reg-entry-time').value = entryTime !== '—' ? entryTime : '';
      document.getElementById('reg-exit-time').value = exitTime !== 'Open' ? exitTime : '';
      this.openModal('modal-regularize');
    },

    // ── Employees Directory View (Admin only) ───────────────────
    async loadEmployeesView() {
      const grid = document.getElementById('employees-grid');
      if (!grid) return;

      const user = window.camsApi.getCurrentUser();
      if (user && user.role === 'employee') {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:2rem; color: var(--text-muted);">Access restricted to administrators.</div>`;
        return;
      }

      grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:2rem;"><div class="spinner"></div></div>`;

      try {
        const search = document.getElementById('emp-search-input')?.value.trim();
        const dept = document.getElementById('emp-dept-filter')?.value;
        const res = await window.camsApi.listEmployees({ page: 1, page_size: 100, search, department: dept });
        this.state.employees = res.items || [];

        if (!this.state.employees.length) {
          grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:2rem; color: var(--text-muted);">No matching employees found.</div>`;
          return;
        }

        grid.innerHTML = this.state.employees.map((emp) => {
          const initials = emp.name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase();
          return `
            <div style="background: var(--bg-surface); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;">
              <div style="display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                  <div class="avatar" style="width: 36px; height: 36px;">${initials}</div>
                  <div>
                    <strong style="font-size: 0.95rem;">${emp.name}</strong>
                    <div style="font-size: 0.74rem; color: var(--text-muted);"><code>${emp.employee_id}</code></div>
                  </div>
                </div>
                <span class="badge ${emp.is_active ? 'badge-success' : 'badge-neutral'}">
                  ${emp.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <div style="font-size: 0.8rem; color: var(--text-muted);">
                <div>${emp.email}</div>
                <div>${emp.department} • ${emp.role}</div>
              </div>
              <div style="display: flex; gap: 0.5rem; margin-top: auto; padding-top: 0.5rem; border-top: 1px solid var(--border-subtle);">
                <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="app.filterAttendanceForEmp('${emp.employee_id}')">
                  Timesheet
                </button>
                <button class="btn btn-secondary btn-sm" onclick="app.deactivateEmployee('${emp.employee_id}')" title="Deactivate" style="color: var(--danger);">
                  ✕
                </button>
              </div>
            </div>
          `;
        }).join('');
      } catch (err) {
        grid.innerHTML = `<div style="grid-column: 1/-1; color: var(--danger); text-align:center;">${err.message}</div>`;
      }
    },

    filterAttendanceForEmp(empId) {
      document.getElementById('att-filter-emp').value = empId;
      this.switchView('attendance');
    },

    async deactivateEmployee(empId) {
      if (!confirm(`Deactivate employee account ${empId}?`)) return;
      try {
        await window.camsApi.deleteEmployee(empId);
        this.showToast('success', `Deactivated ${empId}`);
        await this.loadEmployeesView();
      } catch (err) {
        this.showToast('error', err.message);
      }
    },

    // ── Leave View ──────────────────────────────────────────────
    async loadLeaveView() {
      const tableBody = document.getElementById('leave-table-body');
      const holidaysContainer = document.getElementById('holidays-list-container');
      const user = window.camsApi.getCurrentUser();
      const isEmployee = user && user.role === 'employee';

      // Hide Add Holiday button if employee
      const addHolidayBtn = document.querySelector('[data-open-modal="modal-holiday"]');
      if (addHolidayBtn) addHolidayBtn.style.display = isEmployee ? 'none' : '';

      // Adjust Quota button: show for Admin, hide for employee
      const adjustQuotaBtn = document.getElementById('btn-adjust-quota');
      if (adjustQuotaBtn) adjustQuotaBtn.style.display = isEmployee ? 'none' : 'inline-block';

      // Load Quota Balances for employee
      const targetEmpId = isEmployee ? (user.employee_id || user.username) : 'EMP-007';
      try {
        if (targetEmpId) {
          const currentYear = new Date().getFullYear();
          const balanceRes = await window.camsApi.getLeaveBalances(targetEmpId, currentYear);
          if (balanceRes && balanceRes.balances) {
            const b = balanceRes.balances;
            const setCard = (key, valId, subId) => {
              const item = b[key];
              const valEl = document.getElementById(valId);
              const subEl = document.getElementById(subId);
              if (item && valEl) {
                valEl.textContent = `${item.remaining}d`;
                if (subEl) subEl.textContent = `${item.used} used of ${item.allocated}d total (${targetEmpId})`;
              }
            };
            setCard('annual', 'quota-val-annual', 'quota-sub-annual');
            setCard('casual', 'quota-val-casual', 'quota-sub-casual');
            setCard('sick', 'quota-val-sick', 'quota-sub-sick');
            setCard('other', 'quota-val-other', 'quota-sub-other');
          }
        }
      } catch (balErr) {
        console.warn('Leave quota sync note:', balErr.message);
      }

      if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem;"><div class="spinner"></div></td></tr>`;
      }

      try {
        const leaveParams = { page: 1, page_size: 50 };
        if (isEmployee) {
          leaveParams.employee_id = user.employee_id || user.username;
        }

        const leaveRes = await window.camsApi.listLeaves(leaveParams);
        this.state.leaves = leaveRes.items || [];

        if (tableBody) {
          if (!this.state.leaves.length) {
            tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:1.5rem; color: var(--text-muted);">No leave applications found.</td></tr>`;
          } else {
            tableBody.innerHTML = this.state.leaves.map((l) => {
              const isPending = l.status === 'pending';
              const actionsHtml = isEmployee
                ? `<span style="font-size:0.75rem; color:var(--text-muted);">${l.review_note || (isPending ? 'Pending Review' : 'Processed')}</span>`
                : (isPending
                    ? `<button class="btn btn-secondary btn-sm" onclick="app.approveLeave('${l.leave_id}')">Approve</button>
                       <button class="btn btn-secondary btn-sm" onclick="app.rejectLeave('${l.leave_id}')" style="color:var(--danger); margin-left:4px;">Reject</button>`
                    : `<span style="font-size:0.75rem; color:var(--text-muted);">${l.review_note || 'Reviewed'}</span>`);

              return `
                <tr>
                  <td><strong>${l.employee_id}</strong></td>
                  <td style="text-transform: capitalize;">${l.leave_type}</td>
                  <td>${l.start_date} → ${l.end_date}</td>
                  <td>
                    <span class="badge ${l.status === 'approved' ? 'badge-success' : l.status === 'rejected' ? 'badge-danger' : 'badge-warning'}">
                      ${l.status}
                    </span>
                  </td>
                  <td>${actionsHtml}</td>
                </tr>
              `;
            }).join('');
          }
        }

        const holidayRes = await window.camsApi.listHolidays();
        if (holidaysContainer) {
          if (!holidayRes.length) {
            holidaysContainer.innerHTML = `<span style="font-size:0.84rem; color:var(--text-muted);">No declared holidays.</span>`;
          } else {
            holidaysContainer.innerHTML = holidayRes.map((h) => `
              <div style="display:flex; align-items:center; justify-content:space-between; padding:0.6rem 0; border-bottom:1px solid var(--border-subtle);">
                <div>
                  <div style="font-size:0.86rem; font-weight:600;">${h.name}</div>
                  <div style="font-size:0.75rem; color:var(--text-muted);">${h.description || 'Official Holiday'}</div>
                </div>
                <span class="pill-rule">📅 ${h.date}</span>
              </div>
            `).join('');
          }
        }
      } catch (err) {
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="5" style="color:var(--danger); text-align:center;">${err.message}</td></tr>`;
      }
    },

    async approveLeave(leaveId) {
      const note = prompt('Optional approval note:', 'Approved by Manager');
      if (note === null) return;
      try {
        await window.camsApi.approveLeave(leaveId, note);
        this.showToast('success', 'Leave approved.');
        await this.loadLeaveView();
      } catch (err) {
        this.showToast('error', err.message);
      }
    },

    async rejectLeave(leaveId) {
      const reason = prompt('Mandatory rejection reason:');
      if (!reason) return;
      try {
        await window.camsApi.rejectLeave(leaveId, reason);
        this.showToast('warning', 'Leave rejected.');
        await this.loadLeaveView();
      } catch (err) {
        this.showToast('error', err.message);
      }
    },

    // ── Reports View (Read-Only Compliance) ─────────────────────
    async loadReportsView() {
      const reportBody = document.getElementById('report-breakdown-body');
      if (!reportBody) return;

      const user = window.camsApi.getCurrentUser();
      const isEmployee = user && user.role === 'employee';

      // Hide Admin actions (Run audit, export full csv) for employee
      const runAuditBtn = document.querySelector('[data-open-modal="modal-run-audit"]');
      if (runAuditBtn) runAuditBtn.style.display = isEmployee ? 'none' : '';

      reportBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 2rem;"><div class="spinner"></div></td></tr>`;

      try {
        const today = new Date();
        const start = new Date(today);
        start.setDate(today.getDate() - 7);
        const startStr = start.toISOString().split('T')[0];
        const endStr = today.toISOString().split('T')[0];

        const queryParams = { start_date: startStr, end_date: endStr };
        if (isEmployee) {
          queryParams.employee_id = user.employee_id || user.username;
        }

        const report = await window.camsApi.getAttendanceReport(queryParams);

        const csvBtn = document.getElementById('download-csv-btn');
        if (csvBtn) {
          csvBtn.onclick = () => {
            window.open(window.camsApi.getExportCsvUrl(queryParams), '_blank');
          };
        }

        const stats = report.summary || {};
        document.getElementById('rep-total-days').textContent = stats.total_attended_days ?? '0';
        document.getElementById('rep-total-hours').textContent = stats.total_hours_logged ? `${stats.total_hours_logged.toFixed(1)}h` : '0h';
        document.getElementById('rep-daily-avg').textContent = stats.daily_average ? `${stats.daily_average.toFixed(1)}h` : '0h';
        document.getElementById('rep-violations').textContent = stats.violations_count ?? '0';

        const employees = report.employees || [];
        if (!employees.length) {
          reportBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--text-muted);">No attendance records found for this period.</td></tr>`;
          return;
        }

        reportBody.innerHTML = employees.map((emp) => `
          <tr>
            <td><strong>${emp.name}</strong> (<code>${emp.employee_id}</code>)</td>
            <td>${emp.days_attended} / 3 req</td>
            <td>${emp.total_hours.toFixed(1)}h / 15.0h req</td>
            <td>${emp.avg_hours.toFixed(1)}h/day</td>
            <td>
              <span class="badge ${emp.is_compliant ? 'badge-success' : 'badge-danger'}">
                ${emp.is_compliant ? 'Compliant' : 'Non-Compliant'}
              </span>
            </td>
          </tr>
        `).join('');
      } catch (err) {
        reportBody.innerHTML = `<tr><td colspan="5" style="color:var(--danger); text-align:center;">${err.message}</td></tr>`;
      }
    },

    // ── Audit Logs View (Admin only) ────────────────────────────
    async loadAuditView() {
      const tableBody = document.getElementById('audit-table-body');
      if (!tableBody) return;

      const user = window.camsApi.getCurrentUser();
      if (user && user.role === 'employee') {
        tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--text-muted);">Access restricted to administrators.</td></tr>`;
        return;
      }

      tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem;"><div class="spinner"></div></td></tr>`;

      try {
        const res = await window.camsApi.listAuditLogs({ page: 1, page_size: 50 });
        const items = res.items || [];

        if (!items.length) {
          tableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--text-muted);">No audit events recorded yet.</td></tr>`;
          return;
        }

        tableBody.innerHTML = items.map((log) => `
          <tr>
            <td><small>${new Date(log.timestamp).toLocaleString()}</small></td>
            <td><code>${log.actor_id || 'system'}</code></td>
            <td><span class="pill-rule">${log.action}</span></td>
            <td><code>${log.resource_type}:${log.resource_id}</code></td>
            <td><code style="font-size:0.75rem;">${JSON.stringify(log.new_values || {}).slice(0, 50)}...</code></td>
          </tr>
        `).join('');
      } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="5" style="color:var(--danger); text-align:center;">Admin sign-in required: ${err.message}</td></tr>`;
      }
    },

    // ── Tenant Organizations View (Admin only) ──────────────────
    async loadTenantsView() {
      const tableBody = document.getElementById('tenants-table-body');
      if (!tableBody) return;

      const user = window.camsApi.getCurrentUser();
      if (user && user.role === 'employee') {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">Access restricted to administrators.</td></tr>`;
        return;
      }

      tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem;"><div class="spinner"></div></td></tr>`;

      try {
        const res = await window.camsApi.getTenants(0, 50);
        const items = Array.isArray(res) ? res : (res.items || []);

        if (!items.length) {
          tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">No tenant organizations found.</td></tr>`;
          return;
        }

        const currentTenant = window.camsApi.getTenantId();

        tableBody.innerHTML = items.map((t) => {
          const isCurrent = t.tenant_id === currentTenant;
          const settings = t.settings || {};
          const minDays = settings.min_days_per_week ?? 3;
          const minHours = settings.min_hours_per_week ?? 15;
          const minAvg = settings.min_avg_hours_per_day ?? settings.daily_min_average_hours ?? 5;
          const tz = settings.company_timezone || settings.timezone || 'Asia/Kolkata';
          const thresholds = `${minDays}d / ${minHours}h / ${minAvg}h avg`;
          const createdDate = t.created_at ? new Date(t.created_at).toLocaleDateString() : 'N/A';
          const isActive = t.status ? t.status === 'active' : (t.is_active ?? true);

          return `
            <tr>
              <td>
                <code><strong>${t.tenant_id}</strong></code>
                ${isCurrent ? '<span class="badge badge-success" style="margin-left: 6px; font-size: 0.7rem;">Current Active</span>' : ''}
              </td>
              <td><strong>${t.name}</strong></td>
              <td>${t.contact_email || '—'}</td>
              <td>
                <span class="badge ${isActive ? 'badge-success' : 'badge-danger'}">
                  ${isActive ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td><code>${tz}</code></td>
              <td><small>${thresholds}</small></td>
              <td><small>${createdDate}</small></td>
            </tr>
          `;
        }).join('');
      } catch (err) {
        tableBody.innerHTML = `<tr><td colspan="7" style="color:var(--danger); text-align:center;">Failed to load organizations: ${err.message}</td></tr>`;
      }
    },
  };

  window.app = app;
  app.init();
});
