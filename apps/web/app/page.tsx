import { LandingExperience } from "@/components/landing-experience";
import { SiteHeader } from "@/components/site-header";

export default function HomePage() {
  return (
    <div className="landing-page">
      <SiteHeader />
      <LandingExperience />
    </div>
  );
}
