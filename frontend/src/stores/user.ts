import {defineStore} from 'pinia';
import { AdminUserDTO, UpdateMeDTO, ManagedUserVM } from '@/generated/client';
import {Role} from '@/enums';
import {getLocalToken, removeLocalToken, saveLocalToken} from '@/utils';
import {useMainStore} from '@/stores/main';
import {TYPE} from 'vue-toastification';
import {openapi} from "@/api-v2";

interface State {
  token: string;
  isLoggedIn: boolean | null;
  loginError: string | null;
  userProfile: AdminUserDTO | null;
}

export const useUserStore = defineStore('user', {
  state: (): State => ({
    token: '',
    isLoggedIn: null,
    loginError: null,
    userProfile: null,
  }),
  getters: {
    hasAdminAccess(state: State) {
      const rolesArray = state.userProfile?.roles ? Array.from(state.userProfile.roles) : [];
      return state.userProfile && rolesArray.includes(Role.ADMIN) && state.userProfile.enabled;
    },
  },
  actions: {
    async login(payload: { username: string; password: string }) {
      const mainStore = useMainStore();
      try {
        const response = await openapi.userJwt.authorize({
          loginVM: {
            username: payload.username,
            password: payload.password
          }
        });

        const idToken = response.idToken;
        if (idToken) {
          saveLocalToken(idToken);
          this.token = idToken;
          this.isLoggedIn = true;
          this.loginError = null;
          await mainStore.getUserProfile();
          await this.routeLoggedIn();
          mainStore.addNotification({content: 'Logged in', color: TYPE.SUCCESS});
        } else {
          await this.logout();
        }
      } catch (err) {
        this.loginError = err.response.data.detail;
        await this.logout();
      }
    },
    async updateUserProfile(payload: UpdateMeDTO) {
      const mainStore = useMainStore();
      const loadingNotification = { content: 'saving', showProgress: true };
      try {
        mainStore.addNotification(loadingNotification);
        this.userProfile = await openapi.account.saveAccount({ updateMeDTO: payload });
        mainStore.removeNotification(loadingNotification);
        mainStore.addNotification({ content: 'Profile successfully updated', color: TYPE.SUCCESS });
      } catch (error) {
        await mainStore.checkApiError(error);
        throw new Error(error.response.data.detail);
      }
    },
    async checkLoggedIn() {
      const mainStore = useMainStore();

      const fetchUserAndAppSettings = async () => {
        const response = await openapi.settings.getApplicationSettings();
        this.isLoggedIn = true;

        if (response && response.user && response.app) {
          this.userProfile = response.user;
          mainStore.setAppSettings(response.app);
        }
      };

      if (mainStore.authAvailable && !this.isLoggedIn) {
        this.token = this.token || getLocalToken() || '';
        if (this.token) {
          await fetchUserAndAppSettings();
        } else {
          this.removeLogin();
        }
      } else if (!this.isLoggedIn) {
        await fetchUserAndAppSettings();
      }
    },
    removeLogin() {
      removeLocalToken();
      this.token = '';
      this.isLoggedIn = false;
    },
    async logout() {
      this.removeLogin();
      await this.routeLogout();
    },
    async userLogout() {
      const mainStore = useMainStore();
      await this.logout();
      mainStore.addNotification({ content: 'Logged out', color: TYPE.SUCCESS });
    },
    async routeLogout() {
      // @ts-ignore
      const router = this.$router;
      if (router.currentRoute.path !== '/auth/login') {
        await router.push('/auth/login');
      }
    },
    async routeLoggedIn() {
      // @ts-ignore
      const router = this.$router;
      if (router.currentRoute.path === '/auth/login' || router.currentRoute.path === '/') {
        await router.push('/main');
      }
    },
    async passwordRecovery(payload: { email: string }) {
      const mainStore = useMainStore();
      const loadingNotification = { content: 'Sending password recovery email', showProgress: true };
      try {
        mainStore.addNotification(loadingNotification);
        await openapi.account.requestPasswordReset({ passwordResetRequest: { email: payload.email } });
        mainStore.removeNotification(loadingNotification);
        mainStore.addNotification({ color: TYPE.SUCCESS, content: 'Password recovery link has been sent' });
        await this.logout();
      } catch (error) {
        mainStore.removeNotification(loadingNotification);
        let data = error.response.data;
        let errMessage = '';
        if (data.message === 'error.validation') {
          errMessage = data.fieldErrors.map(e => `${e.field}: ${e.message}`).join('\n');
        } else {
          errMessage = data.detail;
        }
        mainStore.addNotification({ color: TYPE.ERROR, content: errMessage });
      }
    },
    async resetPassword(payload: { password: string; token: string }) {
      const mainStore = useMainStore();
      const loadingNotification = { content: 'Resetting password', showProgress: true };
      mainStore.addNotification(loadingNotification);
      await openapi.account.finishPasswordReset({ tokenAndPasswordVM: { token: payload.token, newPassword: payload.password } });
      mainStore.removeNotification(loadingNotification);
      mainStore.addNotification({ color: TYPE.SUCCESS, content: 'Password successfully changed' });
      await this.logout();
    },
    async signupUser(payload: { userData: ManagedUserVM }) {
      const mainStore = useMainStore();
      const loadingNotification = { content: 'saving', showProgress: true };
      try {
        mainStore.addNotification(loadingNotification);
        await openapi.account.registerAccount({ managedUserVM: payload.userData });
        mainStore.removeNotification(loadingNotification);
        mainStore.addNotification({ content: 'Success! Please proceed to login', color: TYPE.SUCCESS });
        await this.logout();
      } catch (error) {
        throw new Error(error.response.data.detail);
      }
    },
  },
});
