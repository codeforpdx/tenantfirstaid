import { Link } from "react-router-dom";
import BackLink from "./shared/components/BackLink";
import { useEffect } from "react";

export default function Disclaimer() {
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  return (
    <div className="flex items-center pt-16 sm:pt-32 sm:pb-16">
      <div className="relative max-w-2xl m-auto p-8 bg-[#F4F4F2] rounded-lg shadow-md">
        <BackLink />
        <h2 className="text-2xl font-semibold mt-6 mb-2">Disclaimer</h2>
        <p>
          These Terms of Service ("<span className="underline">Terms</span>")
          apply to your access to and use of the websites, chatbots,
          applications and other online products and services (collectively, our
          "<span className="underline">Services</span>") provided by Tenant
          First Aid, a program by Qiu Qiu Law and Code PDX ("
          <span className="underline">Tenant First Aid</span>" or "
          <span className="underline">we</span>"). By accessing or using our
          services, you agree to these Terms. If you do not agree to these
          Terms, including the mandatory arbitration provision and class action
          waiver in Section 14, do not access or use our Services.
        </p>
        <p className="my-4">
          If you have any questions about these Terms or our Services, please
          contact us at{" "}
          <Link
            to="mailto:michael@qiu-qiulaw.com"
            className="underline text-blue-600"
          >
            michael@qiu-qiulaw.com
          </Link>
          .
        </p>
        <h3 className="text-xl font-semibold my-4">1. Eligibility</h3>
        <p>
          You must be at least 18 years of age and a resident of Oregon to
          access or use our Services. If you are under 18 years of age, you may
          only access or use our Services under the supervision of a parent or
          legal guardian who agrees to be bound by these Terms. If you are
          accessing or using our Services on behalf of another person or entity,
          you represent that you are authorized to accept these Terms on that
          person’s behalf and that the person agrees to be responsible to us if
          you or the other person or entity violates these Terms.
        </p>
        <h3 className="text-xl font-semibold my-4">2. Privacy</h3>
        <p>
          Please refer to our{" "}
          <Link to="/privacy-policy" className="underline text-blue-600">
            Privacy Policy
          </Link>{" "}
          for information about how we collect, use and disclose information
          about you.
        </p>
        <h3 className="text-xl font-semibold my-4">3. User Content</h3>
        <p>
          Our Services may allow you to create, store and share information,
          including messages, text and other materials (collectively, "
          <span className="underline">User Content</span>"). Except for the
          license you grant below, you retain all rights in and to your User
          Content, as between you and Tenant First Aid.
        </p>
        <p className="my-4">
          You grant Tenant First Aid a nonexclusive, royalty-free, worldwide,
          fully-paid, and sub-licensable license to use, reproduce, modify,
          adapt, translate, create derivative works from and distribute your
          User Content and any name or likeness provided in connection with your
          User Content for the purpose of providing the Services to you or
          improving the Services, or to enable Tenant First Aid or its partner
          organizations to develop similar services, without compensation to
          you.
        </p>
        <p>
          You may not create, post, store or share any User Content that
          violates these Terms or for which you do not have all the rights
          necessary to grant us the license described above. Although we have no
          obligation to screen, edit or monitor User Content, we may delete or
          remove User Content at any time and for any reason.
        </p>
        <h3 className="text-xl font-semibold my-4">
          4. Prohibited Conduct and Content
        </h3>
        <p>
          You will not violate any applicable law, contract, intellectual
          property or other third-party right or commit a tort, and you are
          solely responsible for your conduct while accessing or using our
          Services. You will not:
        </p>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            Engage in any harassing, threatening, intimidating, predatory or
            stalking conduct
          </li>
          <li>
            Use or attempt to use another user’s account without authorization
            from that user and Tenant First Aid
          </li>
          <li>
            Use our Services in any manner that could interfere with, disrupt,
            negatively affect or inhibit other users from fully enjoying our
            Services or that could damage, disable, overburden or impair the
            functioning of our Services in any manner
          </li>
          <li>
            Reverse engineer any aspect of our Services or do anything that
            might discover source code or bypass or circumvent measures employed
            to prevent or limit access to any part of our Services
          </li>
          <li>
            Attempt to circumvent any content-filtering techniques we employ or
            attempt to access any feature or area of our Services that you are
            not authorized to access
          </li>
          <li>
            Develop or use any third-party applications that interact with our
            Services without our prior written consent, including any scripts
            designed to scrape or extract data from our Services
          </li>
          <li>
            Use our Services for any illegal or unauthorized purpose, or engage
            in, encourage or promote any activity that violates these Terms
          </li>
        </ul>
        <p className="my-4">
          You may also only upload User Content that you have all necessary
          rights to disclose. You may not create, or share any User Content
          that:
        </p>
        <ul className="list-disc list-outside my-4 pl-4">
          <li>
            Is unlawful, libelous, defamatory, obscene, indecent, lewd,
            suggestive, harassing, threatening, invasive of privacy or publicity
            rights, abusive, inflammatory or fraudulent
          </li>
          <li>
            Would constitute, encourage or provide instructions for a criminal
            offense, violate the rights of any party or otherwise create
            liability or violate any local, state, national or international law
          </li>
          <li>
            May infringe any patent, trademark, trade secret, copyright or other
            intellectual or proprietary right of any party
          </li>
          <li>
            Contains any statements, remarks or claims that do not reflect your
            honest views and experiences
          </li>
          <li>
            Impersonates, or misrepresents your affiliation with, any person or
            entity
          </li>
          <li>
            Contains any viruses, corrupted data or other harmful, disruptive or
            destructive files or content
          </li>
          <li>
            Is, in our sole judgment, objectionable or that restricts or
            inhibits any other person from using or enjoying our Services, or
            that may expose Tenant First Aid or others to any harm or liability
            of any type
          </li>
        </ul>
        <h3 className="text-xl font-semibold my-4">
          5. Limited License; Copyright and Trademark
        </h3>
        <p>
          Our Services and the legal information, text, graphics, images,
          photographs, videos, illustrations, trademarks, trade names, service
          marks, logos, slogans and other content contained therein
          (collectively, the "
          <span className="underline">Tenant First Aid Content</span>") are
          owned by or licensed to Tenant First Aid and are protected under both
          United States and foreign laws. Except as explicitly stated in these
          Terms, Tenant First Aid and our licensors reserve all rights in and to
          our Services and the Tenant First Aid Content. You are hereby granted
          a limited, nonexclusive, nontransferable, non-sublicensable, revocable
          license to access and use our Services and Tenant First Aid Content
          for your own personal use; however, such license is subject to these
          Terms and does not include any right to (a) sell, resell or
          commercially use our Services or Tenant First Aid Content; (b) copy,
          reproduce, distribute, publicly perform or publicly display Tenant
          First Aid Content, except as expressly permitted by us or our
          licensors (which includes using the legal information provided through
          the services for the purpose of informing your approach to
          landlord/tenant disputes); (c) modify the Tenant First Aid Content or
          remove any proprietary rights notices or markings from Tenant First
          Aid Content; (d) use any data mining, robots or similar data gathering
          or extraction methods; and (e) use our Services or Tenant First Aid
          Content other than for their intended purposes. Any use of our
          Services or Tenant First Aid Content other than as specifically
          authorized herein, without our prior written permission, is strictly
          prohibited and will terminate the license granted herein.
        </p>
        <h3 className="text-xl font-semibold my-4">6. Feedback</h3>
        <p>
          Any questions, comments, suggestions, ideas, original or creative
          materials or other information you submit about Tenant First Aid or
          our products or Services (collectively, "
          <span className="underline">Feedback</span>"), is non-confidential and
          will become the sole property of Tenant First Aid. We will own
          exclusive rights, including, without limitation, all intellectual
          property rights, in and to Feedback and will be entitled to the
          unrestricted use and dissemination of Feedback for any purpose,
          commercial or otherwise, without acknowledgment or compensation to
          you.
        </p>
        <h3 className="text-xl font-semibold my-4">
          7. Information Not Legal Advice
        </h3>
        <p>
          The Services and Tenant First Aid Content provided through the
          Services are not legal advice. Legal information is not the same as
          legal advice, which is the application of law to an individual’s
          specific circumstances. The Tenant First Aid Services are not a
          substitute for and do not replace the advice or representation of a
          licensed attorney. Although Tenant First Aid goes to great lengths to
          make sure the Tenant First Aid Content is accurate and up to date, we
          make no claim as to the accuracy of the Tenant First Aid Content and
          are not responsible for any consequences that may result from the use
          of the Services. We recommend that you consult with a licensed
          attorney if you want assurance that the information on the Services
          and your interpretation of it are appropriate for your particular
          situation. You should not and are not authorized to rely on the
          Services or Tenant First Aid Content as a source of legal advice. The
          use of the Services does not create an attorney-client relationship
          between you or any user and Qiu Qiu Law or any of its providers,
          partners or affiliated organizations.
        </p>
        <h3 className="text-xl font-semibold my-4">8. Indemnification</h3>
        <p>
          To the fullest extent permitted by applicable law, you will indemnify,
          defend, and hold harmless Tenant First Aid, Qiu Qiu Law, Code PDX, and
          its respective partners and affiliated organizations and each of our
          and their respective officers, directors, agents, partners and
          employees (individually and collectively, the "
          <span className="underline">Tenant First Aid Parties</span>") from and
          against any loss, liability, claim, demand, damages, expenses or costs
          ("
          <span className="underline">Claims</span>") arising out of or related
          to (a) your access to or use of our Services; (b) your User Content or
          Feedback; (c) your violation of these Terms; (d) your violation,
          misappropriation or infringement of any rights of another (including
          intellectual property rights or privacy rights); or (e) your conduct
          in connection with our Services. You agree to promptly notify us of
          any third party Claims, cooperate with the Tenant First Aid Parties in
          defending such Claims and pay all fees, costs and expenses associated
          with defending such Claims (including, but not limited to, attorneys’
          fees). You also agree that the Tenant First Aid Parties will have
          control of the defense or settlement of any third party Claims. This
          indemnity is in addition to, and not in lieu of, any other indemnities
          set forth in a written agreement between you and Tenant First Aid or
          the other Tenant First Aid Parties.
        </p>
        <h3 className="text-xl font-semibold my-4">9. Disclaimers</h3>
        <p>
          We do not control, endorse or take responsibility for any User Content
          or third-party content available on or linked to by our Services.
        </p>
        <p className="my-4">
          Your use of our Services is at your sole risk. Our Services are
          provided “as is” and “as available” without warranties of any kind,
          either express or implied, including, but not limited to, implied
          warranties of merchantability, fitness for a particular purpose,
          title, and non-infringement. In addition, Tenant First Aid does not
          represent or warrant that our Services are accurate, complete,
          reliable, current or error-free. While Tenant First Aid attempts to
          make your access to and use of our Services safe, we cannot and do not
          represent or warrant that our Services or servers are free of viruses
          or other harmful components. You assume the entire risk as to the
          quality and performance of the Services.
        </p>
        <h3 className="text-xl font-semibold my-4">
          10. Limitation of Liability
        </h3>
        <p>
          Tenant First Aid and the other Tenant First Aid Parties will not be
          liable to you under any theory of liability—whether based in contract,
          tort, negligence, strict liability, warranty, or otherwise—for any
          indirect, consequential, exemplary, incidental, punitive or special
          damages or lost profits, even if Tenant First Aid or the other Tenant
          First Aid Parties have been advised of the possibility of such
          damages.
        </p>
        <p className="my-4">
          The total liability of Tenant First Aid and the other Tenant First Aid
          Parties, for any claim arising out of or relating to these Terms or
          our Services, regardless of the form of the action, is limited to the
          amount paid, if any, by you to access or use our Services.
        </p>
        <p className="my-4">
          The limitations set forth in this section will not limit or exclude
          liability for the gross negligence, fraud or intentional misconduct of
          Tenant First Aid or the other Tenant First Aid Parties or for any
          other matters in which liability cannot be excluded or limited under
          applicable law. Additionally, some jurisdictions do not allow the
          exclusion or limitation of incidental or consequential damages, so the
          above limitations or exclusions may not apply to you.
        </p>
        <h3 className="text-xl font-semibold my-4">11. Release</h3>
        <p>
          To the fullest extent permitted by applicable law, you release Tenant
          First Aid and the other Tenant First Aid Parties from responsibility,
          liability, claims, demands, and/or damages (actual and consequential)
          of every kind and nature, known and unknown (including, but not
          limited to, claims of negligence), arising out of or related to
          disputes between users and the acts or omissions of third parties. You
          expressly waive any rights you may have under any statute or common
          law principles that would otherwise limit the coverage of this release
          to include only those claims which you may know or suspect to exist in
          your favor at the time of agreeing to this release.
        </p>
        <h3 className="text-xl font-semibold my-4">
          12. Transfer and Processing Data
        </h3>
        <p>
          By accessing or using our Services, you consent to the processing,
          transfer and storage of information about you in and to the United
          States and other countries, where you may not have the same rights and
          protections as you do under local law.
        </p>
        <h3 className="text-xl font-semibold my-4">
          13. Electronic Communications
        </h3>
        <p>
          By creating a Tenant First Aid account or using the Services, you also
          consent to receive electronic communications from Tenant First Aid
          (e.g., via email, text or by posting notices on our Services). These
          communications may include notices about your account or reminders
          related to your use of the Services and are part of your relationship
          with us. You agree that any notices, agreements, disclosures or other
          communications that we send to you electronically will satisfy any
          legal communication requirements, including, but not limited to, that
          such communications be in writing.
        </p>
        <h3 className="text-xl font-semibold my-4">
          14. Dispute Resolution; Binding Arbitration
        </h3>
        <p>
          Please read the following section carefully because it requires you to
          arbitrate certain disputes and claims with Tenant First Aid and limits
          the manner in which you can seek relief from us.
        </p>
        <p className="my-4">
          Except for small claims disputes in which you or Tenant First Aid seek
          to bring an individual action in small claims court located in the
          county of your billing address or disputes in which you or Tenant
          First Aid seeks injunctive or other equitable relief for the alleged
          unlawful use of intellectual property, you and Tenant First Aid waive
          your rights to a jury trial and to have any dispute arising out of or
          related to these Terms or our Services resolved in court. Instead, all
          disputes arising out of or relating to these Terms or our Services
          will be resolved through confidential binding arbitration held in
          Multnomah County, Oregon in accordance with the Streamlined
          Arbitration Rules and Procedures ("
          <span className="underline">Rules</span>") of the Judicial Arbitration
          and Mediation Services ("<span className="underline">JAMS</span>"),
          which are available on the JAMS website and hereby incorporated by
          reference. You either acknowledge and agree that you have read and
          understand the rules of JAMS or waive your opportunity to read the
          rules of JAMS and any claim that the rules of JAMS are unfair or
          should not apply for any reason.
        </p>
        <p className="my-4">
          You and Tenant First Aid agree that any dispute arising out of or
          related to these Terms or our Services is personal to you and Tenant
          First Aid and that any dispute will be resolved solely through
          individual arbitration and will not be brought as a class arbitration,
          class action or any other type of representative proceeding.
        </p>
        <p className="my-4">
          You and Tenant First Aid agree that these Terms affect interstate
          commerce and that the enforceability of this Section 14 will be
          substantively and procedurally governed by the Federal Arbitration
          Act, 9 U.S.C. § 1, et seq. (the "
          <span className="underline">FAA</span>"), to the maximum extent
          permitted by applicable law. As limited by the FAA, these Terms and
          the JAMS Rules, the arbitrator will have exclusive authority to make
          all procedural and substantive decisions regarding any dispute and to
          grant any remedy that would otherwise be available in court; provided,
          however, that the arbitrator does not have the authority to conduct a
          class arbitration or a representative action, which is prohibited by
          these Terms. The arbitrator may only conduct an individual arbitration
          and may not consolidate more than one individual’s claims, preside
          over any type of class or representative proceeding or preside over
          any proceeding involving more than one individual. You agree that for
          any arbitration you initiate, you will pay the filing fee and we will
          pay the remaining JAMS fees and costs. For any arbitration initiated
          by us, we will pay all JAMS fees and costs. You and Tenant First Aid
          agree that the state or federal courts of the State of Illinois and
          the United States sitting in Multnomah County, Oregon have exclusive
          jurisdiction over any appeals and the enforcement of an arbitration
          award.
        </p>
        <p className="my-4">
          ANY CLAIM ARISING OUT OF OR RELATED TO THESE TERMS OR OUR SERVICES
          MUST BE FILED WITHIN ONE YEAR AFTER SUCH CLAIM AROSE; OTHERWISE, THE
          CLAIM IS PERMANENTLY BARRED, WHICH MEANS THAT YOU AND TENANT FIRST AID
          WILL NOT HAVE THE RIGHT TO ASSERT THE CLAIM.
        </p>
        <p className="my-4">
          You have the right to opt out of binding arbitration within thirty
          (30) days of the date you first accepted the terms of this Section 14
          by sending an email to{" "}
          <Link
            to="mailto:michael@qiu-qiulaw.com"
            className="underline text-blue-600"
          >
            michael@qiu-qiulaw.com
          </Link>{" "}
          in order to be effective, the opt out notice must include your full
          name and clearly indicate your intent to opt out of binding
          arbitration. By opting out of binding arbitration, you are agreeing to
          resolve Disputes in accordance with this Section 14.
        </p>
        <h3 className="text-xl font-semibold my-4">
          15. Governing Law and Venue
        </h3>
        <p>
          These Terms and your access to and use of our Services will be
          governed by and construed and enforced in accordance with the laws of
          Oregon, without regard to conflict of law rules or principles (whether
          of Oregon or any other jurisdiction) that would cause the application
          of the laws of any other jurisdiction. Any dispute between the parties
          that is not subject to arbitration or cannot be heard in small claims
          court will be resolved in the state or federal courts of Oregon and
          the United States, respectively, sitting in Multnomah County, Oregon.
        </p>
        <h3 className="text-xl font-semibold my-4">
          16. Changes to these Terms
        </h3>
        <p>
          We may make changes to these Terms from time to time. If we make
          changes, we will post the amended Terms to our Services and update the
          “Last Updated” date above. Unless we say otherwise in our notice, the
          amended Terms will be effective immediately and your continued access
          to and use of our Services after we provide notice will confirm your
          acceptance of the changes. If you do not agree to the amended Terms,
          you must stop accessing and using our Services.
        </p>
        <h3 className="text-xl font-semibold my-4">
          17. Additional Terms for Specific Services
        </h3>
        <p>
          In addition to these Terms, we may ask you to accept additional terms
          that apply to specific features, products or services. To the extent
          any additional terms conflict with these Terms, the additional terms
          govern with respect to your access to or use of the applicable
          feature, product or service.
        </p>
        <h3 className="text-xl font-semibold my-4">18. Termination</h3>
        <p>
          We reserve the right, without notice and in our sole discretion, to
          terminate your right to access or use our Services. We are not
          responsible for any loss or harm related to your inability to access
          or use our Services.
        </p>
        <h3 className="text-xl font-semibold my-4">19. Severability</h3>
        <p>
          If any provision or part of a provision of these Terms is unlawful,
          void or unenforceable, that provision or part of the provision is
          deemed severable from these Terms and does not affect the validity and
          enforceability of any remaining provisions.
        </p>
        <h3 className="text-xl font-semibold my-4">20. Miscellaneous</h3>
        <p>
          These Terms constitute the entire agreement between you and Tenant
          First Aid relating to your access to and use of our Services. The
          failure of Tenant First Aid to exercise or enforce any right or
          provision of these Terms will not operate as a waiver of such right or
          provision. The section titles in these Terms are for convenience only
          and have no legal or contractual effect. Except as otherwise provided
          herein, these Terms are intended solely for the benefit of the parties
          and are not intended to confer third party beneficiary rights upon any
          other person or entity.
        </p>
      </div>
    </div>
  );
}
