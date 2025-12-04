import { Link } from "react-router-dom";
import BackLink from "./shared/components/BackLink";
import { useEffect } from "react";
import { CONTACT_EMAIL } from "./shared/constants/constants";

export default function PrivacyPolicy() {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="flex items-center pt-16 sm:pt-32 sm:pb-16">
      <div className="relative max-w-2xl m-auto p-8 bg-[#F4F4F2] rounded-lg shadow-md">
        <BackLink />
        <h2 className="text-2xl font-semibold mt-6">Privacy Policy</h2>
        <em>Last Updated: June 19, 2025</em>
        <p className="my-4">
          Tenant First Aid, a program of Code PDX and Qiu Qiu Law ("
          <span className="underline">Tenant First Aid</span>
          ") provides a chatbot service and other tools that allow Oregon
          residents to access legal information free of charge about common
          tenant issues. This Privacy Policy explains how Qiu Qiu Law collects,
          uses, and discloses information about you through its websites and
          other online products and services (collectively, the "
          <span className="underline">Services</span>
          ") or when you otherwise interact with us.
        </p>
        <p className="my-4">
          We may change this Privacy Policy from time to time. If we make
          changes, we will notify you by revising the date at the top of the
          policy and, in some cases, we may provide you with additional notice
          (such as adding a statement to our homepage or sending you a
          notification). We encourage you to review the Privacy Policy whenever
          you access the Services or otherwise interact with us to stay informed
          about our information practices and the choices available to you.
        </p>
        <h3 className="text-xl font-semibold my-4 flex flex-col">
          <span>Collection of Information</span>
          <span>Information You Provide to Us</span>
        </h3>
        <p>
          We collect transcripts of all conversations for quality improvement
          purposes. We do not encourage you to provide your name, address, or
          other sensitive information, and generally do not need it to answer
          the type of general questions that Tenant First Aid is meant for.
        </p>
        <p className="my-4">
          When you access or use our Services, we automatically collect
          information about you, including:
        </p>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            Log Information: We collect log information about your use of the
            Services, including the type of browser you use, access times, pages
            viewed, your IP address and the page you visited before navigating
            to our Services.
          </li>
          <li>
            Device Information: We collect information about the computer or
            mobile device you use to access our Services, including the hardware
            model, operating system and version, unique device identifiers, and
            mobile network information.
          </li>
          <li>
            Information Collected by Cookies and Other Tracking Technologies:
            Like most online services and mobile applications, we may use
            cookies and other technologies, such as web beacons and web storage
            to collect information about your activity, browser, and device.
            Cookies are small data files stored on your hard drive or in device
            memory that help us improve our Services and your experience, see
            which types of legal information are most frequently accessed
            through our Services, and count visits. Web beacons are electronic
            images that may be used in our Services or emails and help deliver
            cookies, count visits and understand usage and campaign
            effectiveness. For more information about cookies and how to disable
            them, please see “Your Choices” below.
          </li>
          <li>
            Other Venders: Our Services connect with other technology platforms
            and anonymously shared/stored data is governed by their policies
            (Google:{" "}
            <Link
              to="https://policies.google.com/privacy"
              className="underline text-blue-600"
            >
              Privacy Policy
            </Link>{" "}
            and{" "}
            <Link
              to="https://policies.google.com/terms"
              className="underline text-blue-600"
            >
              Terms of Service
            </Link>
            )
          </li>
        </ul>
        <h3 className="text-xl font-semibold my-4">Use of Information</h3>
        <p>
          We use the information we collect to provide, maintain, and improve
          our services, such as to track Service usage and improve the Services.
          We may also use the information we collect to:
        </p>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            Send you technical notices, updates, security alerts and support and
            administrative messages and to respond to your comments, questions
            and customer service requests
          </li>
          <li>
            Provide news and information we think will be of interest to you
          </li>
          <li>
            Monitor and analyze trends, usage and activities in connection with
            our Services
          </li>
          <li>
            Detect, investigate and prevent fraudulent and illegal activities
            and protect the rights and property of Tenant First Aid and others
          </li>
          <li>
            Personalize and improve the Services and provide content or features
            that match user needs
          </li>
          <li>
            Carry out any other purpose described to you at the time the
            information was collected
          </li>
        </ul>
        <h3 className="text-xl font-semibold my-4">Sharing of Information</h3>
        <p>
          We may share information about you as follows or as otherwise
          described in this Privacy Policy:
        </p>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            With vendors, consultants and other service providers who need
            access to such information to carry out work on our behalf
          </li>
          <li>
            With one of our legal services partner organizations, if you apply
            for legal aid
          </li>
          <li>
            In response to a request for information if we believe disclosure is
            in accordance with, or required by, any applicable law or legal
            process, including lawful requests by public authorities to meet
            national security or law enforcement requirements
          </li>
        </ul>
        <h3 className="text-xl font-semibold my-4 flex flex-col">
          <span>Analytics Services</span>
          <span>Provided by Others</span>
        </h3>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            If we believe your actions are inconsistent with our user agreements
            or policies, or to protect the rights, property and safety of Tenant
            First Aid or others
          </li>
          <li>
            Between and among Tenant First Aid and our partner organizations in
            order to provide, evaluate or improve the Services; and
          </li>
          <li>With your consent or at your direction</li>
        </ul>
        <p className="my-4">
          We may also share aggregated or de-identified information, which
          cannot reasonably be used to identify you.
        </p>
        <p className="my-4">
          We may allow others to provide analytics services across the internet
          and in applications. These entities may use cookies, web beacons,
          device identifiers and other technologies to collect information about
          your use of the Services and other websites and applications,
          including your IP address, web browser, mobile network information,
          pages viewed, time spent on pages or in apps, links clicked and
          conversion information. This information may be used by Tenant First
          Aid and others to, among other things, analyze and track data,
          determine the popularity of certain content, deliver content targeted
          to your interests on our Services and other websites and better
          understand your online activity.
        </p>
        <h3 className="text-xl font-semibold my-4">Data Retention</h3>
        <p>
          We store the information we collect about you for as long as is
          necessary for the purpose(s) for which we originally collected it. We
          may retain certain information for legitimate business purposes or as
          required by law.
        </p>
        <h3 className="text-xl font-semibold my-4">
          Transfer of Information to the U.S. and Other Countries
        </h3>
        <p>
          Tenant First Aid is based in the United States and we process and
          store information in the U.S.
        </p>
        <h3 className="text-xl font-semibold my-4 flex flex-col">
          <span>Your Choices</span>
          <span>Personal Information</span>
        </h3>
        <p>
          You may update, correct or delete information about you at any time by
          interacting with the Services, or emailing us at{" "}
          <Link
            to={`mailto:${CONTACT_EMAIL}`}
            className="underline text-blue-600"
            aria-label="contact-email"
          >
            {CONTACT_EMAIL}
          </Link>
          . We may also retain cached or archived copies of information about
          you for a certain period of time.
        </p>
        <h3 className="text-xl font-semibold my-4">Cookies</h3>
        <p>
          Most web browsers are set to accept cookies by default. If you prefer,
          you can usually choose to set your browser to remove or reject browser
          cookies. Please note that if you choose to remove or reject cookies,
          this could affect the availability and functionality of our Services.
        </p>
        <h3 className="text-xl font-semibold my-4">
          Mobile Notifications/Alerts
        </h3>
        <p>With your consent, we may send alerts to your mobile device.</p>
        <h3 className="text-xl font-semibold my-4">Contact Us</h3>
        <p>
          If you have any questions about this Privacy Policy, please contact us
          at:{" "}
          <Link
            to={`mailto:${CONTACT_EMAIL}`}
            className="underline text-blue-600"
            aria-label="contact-email"
          >
            {CONTACT_EMAIL}
          </Link>
        </p>
      </div>
    </div>
  );
}
