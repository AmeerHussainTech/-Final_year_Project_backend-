declare module 'firebase/app' {
  export function initializeApp(config: any): any;
  export function getApps(): any[];
}

declare module 'firebase/auth' {
  export function getAuth(app?: any): any;
  export class GoogleAuthProvider {
    constructor();
  }
  export function signInWithPopup(auth: any, provider: any): Promise<any>;
  export function signInWithRedirect(auth: any, provider: any): Promise<any>;
  export function updateProfile(user: any, profile: { displayName?: string; photoURL?: string }): Promise<any>;
  export function signInWithEmailAndPassword(auth: any, email: string, pass: string): Promise<any>;
  export function createUserWithEmailAndPassword(auth: any, email: string, pass: string): Promise<any>;
}
